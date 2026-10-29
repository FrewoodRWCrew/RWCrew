"use client";

// The browser's own (free) speech recognition, the Web Speech API, for the
// phone's voice count: start() on the first tap of the microphone button,
// stop() on the second (or the browser stops by itself after a pause); the
// recognised sentence is handed to onFinal when it's done. Works in Chrome on
// Android and Safari on iPhone (both send the audio to their own speech
// service, so it needs a network), only over HTTPS or on localhost.
// Firefox has no speech recognition: `supported` is then false.
//
// iPhone quirks handled here:
// - continuous listening is buggy (results never become "final"), so iOS
//   listens one sentence at a time, and the last interim text counts when no
//   final text came;
// - in the home-screen app the recognition often ends at once without a word
//   or an error: that's reported as "unavailable", so the screen can point to
//   the keyboard's own dictation instead of staying silent;
// - with Dictation (Siri) switched off it answers "service-not-allowed".

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
  onstart: (() => void) | null;
  onaudiostart: (() => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}
type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

/** Why listening failed, each with its own message on the screen. */
export type SpeechFailure = "denied" | "dictationOff" | "network" | "unavailable" | "failed";

// A recognition that ends this quickly without hearing anything didn't really run.
const DEAD_START_MS = 1500;

/** The browser's SpeechRecognition class (Safari/Chrome still prefix it), if any. */
function getRecognitionClass(): SpeechRecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const speechWindow = window as unknown as {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition ?? null;
}

/** True on an iPhone/iPad (iPadOS presents itself as a Mac with a touch screen). */
export function isIos(): boolean {
  if (typeof navigator === "undefined") return false;
  return /iPad|iPhone|iPod/.test(navigator.userAgent) || (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1);
}

// Support never changes while the page is open: nothing to subscribe to.
const subscribeNever = () => () => {};

interface UseSpeechRecognitionOptions {
  /** BCP-47 language, e.g. "nl-BE" or "en-GB". */
  lang: string;
  /** Called with the whole recognised sentence after each listening turn. */
  onFinal: (text: string) => void;
  /** Called when listening failed (no permission, no network, ...). */
  onFailure: (failure: SpeechFailure) => void;
  /** Called with a short line per recognition event (the screen's ?debug=1 log). */
  onDebug?: (line: string) => void;
}

export function useSpeechRecognition({ lang, onFinal, onFailure, onDebug }: UseSpeechRecognitionOptions) {
  // Whether this browser can recognise speech at all (false while rendering on the server).
  const supported = useSyncExternalStore(
    subscribeNever,
    () => getRecognitionClass() !== null,
    () => false,
  );
  const [listening, setListening] = useState(false);
  // The words heard so far during this turn, shown live under the button.
  const [interimText, setInterimText] = useState("");

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  // The final pieces of this turn, and the last not-yet-final text (iOS often never finalises).
  const finalPartsRef = useRef<string[]>([]);
  const lastInterimRef = useRef("");
  // What happened during this turn, to tell a dead start from a quiet user.
  const startedAtRef = useRef(0);
  const heardAudioRef = useRef(false);
  const failedRef = useRef(false);
  const stoppedByUserRef = useRef(false);

  // The latest callbacks, read from the recognition's events so a re-render
  // doesn't need a new recognition object.
  const onFinalRef = useRef(onFinal);
  const onFailureRef = useRef(onFailure);
  const onDebugRef = useRef(onDebug);
  useEffect(() => {
    onFinalRef.current = onFinal;
    onFailureRef.current = onFailure;
    onDebugRef.current = onDebug;
  });

  /** Start listening (first tap). */
  const start = useCallback(() => {
    const Recognition = getRecognitionClass();
    if (!Recognition || recognitionRef.current) return;
    const debug = (line: string) => onDebugRef.current?.(line);

    const recognition = new Recognition();
    recognition.lang = lang;
    // Android keeps listening until the second tap; iOS takes one sentence
    // per turn (its continuous mode loses the results).
    recognition.continuous = !isIos();
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    finalPartsRef.current = [];
    lastInterimRef.current = "";
    heardAudioRef.current = false;
    failedRef.current = false;
    stoppedByUserRef.current = false;
    startedAtRef.current = Date.now();

    recognition.onstart = () => debug("start");
    recognition.onaudiostart = () => {
      heardAudioRef.current = true;
      debug("audiostart");
    };
    recognition.onresult = (event) => {
      let interim = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result.isFinal) finalPartsRef.current.push(result[0].transcript);
        else interim += result[0].transcript;
        debug(`result ${result.isFinal ? "final" : "interim"}: ${result[0].transcript}`);
      }
      lastInterimRef.current = interim.trim();
      setInterimText([...finalPartsRef.current, interim].join(" ").trim());
    };
    recognition.onerror = (event) => {
      debug(`error: ${event.error}`);
      // Silence or a deliberate stop isn't an error worth showing.
      if (event.error === "no-speech" || event.error === "aborted") return;
      failedRef.current = true;
      if (event.error === "not-allowed") onFailureRef.current("denied");
      else if (event.error === "service-not-allowed") onFailureRef.current("dictationOff");
      else if (event.error === "network") onFailureRef.current("network");
      else onFailureRef.current("failed");
    };
    recognition.onend = () => {
      const elapsed = Date.now() - startedAtRef.current;
      debug(`end after ${elapsed} ms`);
      recognitionRef.current = null;
      setListening(false);
      setInterimText("");
      // Everything recognised this turn: the final text, else what was last heard.
      const text = (finalPartsRef.current.join(" ") || lastInterimRef.current).trim();
      finalPartsRef.current = [];
      lastInterimRef.current = "";
      if (text) {
        onFinalRef.current(text);
        return;
      }
      // Ended by itself almost at once, without audio or an error: it didn't really run.
      if (!failedRef.current && !stoppedByUserRef.current && !heardAudioRef.current && elapsed < DEAD_START_MS) {
        onFailureRef.current("unavailable");
      }
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
      setListening(true);
    } catch (error) {
      recognitionRef.current = null;
      debug(`start threw: ${String(error)}`);
      onFailureRef.current("failed");
    }
  }, [lang]);

  /** Stop listening (second tap); the last words still arrive via onend. */
  const stop = useCallback(() => {
    stoppedByUserRef.current = true;
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
