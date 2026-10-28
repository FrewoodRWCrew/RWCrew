"use client";

// The browser's own (free) speech recognition, the Web Speech API, as a
// push-to-talk hook for the phone's voice count: start() while the
// microphone button is held, stop() on release; the recognised sentence is
// handed to onFinal once the browser is done with it. Works in Chrome on
// Android and Safari on iPhone (both send the audio to their own speech
// service, so it needs a network), only over HTTPS or on localhost.
// Firefox has no speech recognition: `supported` is then false.

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

// The few parts of the Web Speech API used here (not in every TypeScript DOM lib).
interface SpeechRecognitionAlternativeLike {
  transcript: string;
}
interface SpeechRecognitionResultLike {
  isFinal: boolean;
  0: SpeechRecognitionAlternativeLike;
}
interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: ArrayLike<SpeechRecognitionResultLike>;
}
interface SpeechRecognitionErrorEventLike {
  error: string;
}
interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}
type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

/** Why listening failed, each with its own message on the screen. */
export type SpeechFailure = "denied" | "network" | "failed";

/** The browser's SpeechRecognition class (Safari/Chrome still prefix it), if any. */
function getRecognitionClass(): SpeechRecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const speechWindow = window as unknown as {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition ?? null;
}

// Support never changes while the page is open: nothing to subscribe to.
const subscribeNever = () => () => {};

interface UseSpeechRecognitionOptions {
  /** BCP-47 language, e.g. "nl-BE" or "en-GB". */
  lang: string;
  /** Called with the whole recognised sentence after each press. */
  onFinal: (text: string) => void;
  /** Called when listening failed (no permission, no network, ...). */
  onFailure: (failure: SpeechFailure) => void;
}

export function useSpeechRecognition({ lang, onFinal, onFailure }: UseSpeechRecognitionOptions) {
  // Whether this browser can recognise speech at all (false while rendering on the server).
  const supported = useSyncExternalStore(
    subscribeNever,
    () => getRecognitionClass() !== null,
    () => false,
  );
  const [listening, setListening] = useState(false);
  // The words heard so far during this press, shown live under the button.
  const [interimText, setInterimText] = useState("");

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  // The final pieces of this press, joined and handed over when it ends.
  const finalPartsRef = useRef<string[]>([]);

  // The latest callbacks, read from the recognition's events so a re-render
  // doesn't need a new recognition object.
  const onFinalRef = useRef(onFinal);
  const onFailureRef = useRef(onFailure);
  useEffect(() => {
    onFinalRef.current = onFinal;
    onFailureRef.current = onFailure;
  });

  /** Start listening (button pressed). */
  const start = useCallback(() => {
    const Recognition = getRecognitionClass();
    if (!Recognition || recognitionRef.current) return;

    const recognition = new Recognition();
    recognition.lang = lang;
    // Keep listening while the button is held; partial words shown live.
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    finalPartsRef.current = [];

    recognition.onresult = (event) => {
      let interim = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result.isFinal) finalPartsRef.current.push(result[0].transcript);
        else interim += result[0].transcript;
      }
      setInterimText([...finalPartsRef.current, interim].join(" ").trim());
    };
    recognition.onerror = (event) => {
      // Silence or a deliberate stop isn't an error worth showing.
      if (event.error === "no-speech" || event.error === "aborted") return;
      if (event.error === "not-allowed" || event.error === "service-not-allowed") onFailureRef.current("denied");
      else if (event.error === "network") onFailureRef.current("network");
      else onFailureRef.current("failed");
    };
    recognition.onend = () => {
      // The browser is done (button released, or it stopped on its own):
      // hand over everything that was recognised during this press.
      recognitionRef.current = null;
      setListening(false);
      setInterimText("");
      const text = finalPartsRef.current.join(" ").trim();
      finalPartsRef.current = [];
      if (text) onFinalRef.current(text);
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
      setListening(true);
    } catch {
      recognitionRef.current = null;
      onFailureRef.current("failed");
    }
  }, [lang]);

  /** Stop listening (button released); the last words still arrive via onend. */
  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  // Leaving the screen while listening: switch the microphone off.
  useEffect(
    () => () => {
      const recognition = recognitionRef.current;
      if (recognition) {
        recognition.onend = null;
        recognition.abort();
      }
    },
    [],
  );

  return { supported, listening, interimText, start, stop };
}
