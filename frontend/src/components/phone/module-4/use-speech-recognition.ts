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
// - with Dictation (Siri) switched off it answers "service-not-allowed";
// - a *new* recognition object made after the first one has run never hears
//   anything again until the page reloads (the voice count only worked once
//   per app start): so one object is made per screen and reused for every
//   turn; a fresh one is only made when the old one is stuck or refuses;
// - after stop() iOS often never sends "end", which left the button on
//   "listening" so it couldn't be restarted: on iOS the stop tap finishes the
//   turn itself (with the text heard so far) and throws the object away;
//   elsewhere a short wait for "end" does the same if it doesn't come.

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
// How long to wait for "end" after a stop tap (not on iOS) before finishing the turn ourselves.
const STOP_WAIT_MS = 2000;

/** Switch a recognition object off for good: no more events, microphone released. */
function discardRecognition(recognition: SpeechRecognitionLike) {
  recognition.onstart = null;
  recognition.onaudiostart = null;
  recognition.onresult = null;
  recognition.onerror = null;
  recognition.onend = null;
  recognition.abort();
}

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

  // The one recognition object of this screen, reused for every turn (see the iPhone quirks above).
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  // Whether a turn is running, and its number: events of an older turn are ignored.
  const turnOpenRef = useRef(false);
  const turnRef = useRef(0);
  // The final pieces of this turn, and the last not-yet-final text (iOS often never finalises).
  const finalPartsRef = useRef<string[]>([]);
  const lastInterimRef = useRef("");
  // What happened during this turn, to tell a dead start from a quiet user.
  const startedAtRef = useRef(0);
  const heardAudioRef = useRef(false);
  const failedRef = useRef(false);
  const stoppedByUserRef = useRef(false);
  // Ends the running turn (set by start(), used by onend and by the stop tap), and the stop tap's wait.
  const finishTurnRef = useRef<((how: string) => void) | null>(null);
  const stopTimerRef = useRef<number | null>(null);

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
    if (!Recognition) return;
    const debug = (line: string) => onDebugRef.current?.(line);
    const discard = discardRecognition;
    // A stop tap's wait of the previous turn no longer matters.
    if (stopTimerRef.current !== null) window.clearTimeout(stopTimerRef.current);
    stopTimerRef.current = null;

    // A previous turn that never reported its end (iOS sometimes doesn't):
    // throw that object away instead of silently ignoring every tap from now on.
    if (recognitionRef.current && turnOpenRef.current) {
      debug("previous turn still open: aborted");
      discard(recognitionRef.current);
      recognitionRef.current = null;
    }

    // Reuse this screen's object; only the very first turn (or after a stuck one) makes a new one.
    const reused = recognitionRef.current !== null;
    const recognition = recognitionRef.current ?? new Recognition();
    recognitionRef.current = recognition;
    debug(reused ? "reusing recognition" : "new recognition");
    const turn = ++turnRef.current;
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

    // This turn's handlers (set again on every turn, also on a reused object).
    const attach = (target: SpeechRecognitionLike) => {
      target.onstart = () => debug("start");
      target.onaudiostart = () => {
        heardAudioRef.current = true;
        debug("audiostart");
      };
      target.onresult = (event) => {
        if (turn !== turnRef.current) return;
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
      target.onerror = (event) => {
        if (turn !== turnRef.current) return;
        debug(`error: ${event.error}`);
        // Silence or a deliberate stop isn't an error worth showing.
        if (event.error === "no-speech" || event.error === "aborted") return;
        failedRef.current = true;
        if (event.error === "not-allowed") onFailureRef.current("denied");
        else if (event.error === "service-not-allowed") onFailureRef.current("dictationOff");
        else if (event.error === "network") onFailureRef.current("network");
        else onFailureRef.current("failed");
      };
      target.onend = () => finish("end");
    };

    /** End this turn once (from "end", or from the stop tap when "end" doesn't come):
     *  hand over the text heard, or report a start that didn't really run. */
    const finish = (how: string) => {
      // A turn that was replaced by a newer one, or already finished, no longer counts.
      if (turn !== turnRef.current || !turnOpenRef.current) return;
      const elapsed = Date.now() - startedAtRef.current;
      debug(`${how} after ${elapsed} ms`);
      if (stopTimerRef.current !== null) window.clearTimeout(stopTimerRef.current);
      stopTimerRef.current = null;
      // The object itself is kept for the next turn (unless the stop tap throws it away).
      turnOpenRef.current = false;
      finishTurnRef.current = null;
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

    /** Start a turn on this object; false when the browser refuses (it throws). */
    const tryStart = (target: SpeechRecognitionLike) => {
      attach(target);
      try {
        target.start();
        return true;
      } catch (error) {
        debug(`start threw: ${String(error)}`);
        return false;
      }
    };

    let started = tryStart(recognition);
    // A reused object that refuses (e.g. "already started"): one more try with a fresh object.
    if (!started && reused) {
      discard(recognition);
      const fresh = new Recognition();
      fresh.lang = lang;
      fresh.continuous = !isIos();
      fresh.interimResults = true;
      fresh.maxAlternatives = 1;
      recognitionRef.current = fresh;
      debug("new recognition (retry)");
      started = tryStart(fresh);
    }
    if (started) {
      turnOpenRef.current = true;
      finishTurnRef.current = finish;
      setListening(true);
    } else {
      if (recognitionRef.current) discard(recognitionRef.current);
      recognitionRef.current = null;
      onFailureRef.current("failed");
    }
  }, [lang]);

  /** Stop listening (second tap). The button must always come back to "talk",
   *  also when the browser never sends "end" (iOS). */
  const stop = useCallback(() => {
    stoppedByUserRef.current = true;
    const recognition = recognitionRef.current;
    if (!turnOpenRef.current || !recognition) {
      // Nothing running (any more): just make sure the button is back.
      setListening(false);
      return;
    }
    if (isIos()) {
      // iOS: finish now with what was heard (its text is mostly interim anyway),
      // then throw the object away so a hanging one can't block the next tap.
      finishTurnRef.current?.("stopped");
      discardRecognition(recognition);
      recognitionRef.current = null;
      return;
    }
    // Elsewhere the last words arrive after stop() via "end"; if it doesn't come, finish anyway.
    recognition.stop();
    stopTimerRef.current = window.setTimeout(() => {
      stopTimerRef.current = null;
      finishTurnRef.current?.("no end, finished");
      if (recognitionRef.current) discardRecognition(recognitionRef.current);
      recognitionRef.current = null;
    }, STOP_WAIT_MS);
  }, []);

  // Leaving the screen: switch the microphone off and drop the object.
  useEffect(
    () => () => {
      if (stopTimerRef.current !== null) window.clearTimeout(stopTimerRef.current);
      if (recognitionRef.current) discardRecognition(recognitionRef.current);
      recognitionRef.current = null;
      turnOpenRef.current = false;
      finishTurnRef.current = null;
    },
    [],
  );

  return { supported, listening, interimText, start, stop };
}
