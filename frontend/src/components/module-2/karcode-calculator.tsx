"use client";

// The calculator behind KarTracker's "Karcode Simulator" (screen key
// "kartracker.karcodesimulator"), shared by the web screen
// (karcode-simulator.tsx) and the phone app (/m/module-2/karcode). The user
// taps (or types) a kar number, or scans the QR code on the kar, and the code
// of that kar's lock appears on a glowing seven-segment display. The code is
// computed by the backend with the formula saved on the Instellingen screen
// (GET /karcode); the formula itself never reaches this screen.

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Copy, Delete, History, LockKeyhole, ScanLine, X } from "lucide-react";
import { toast } from "sonner";
import { getKarcode } from "@/lib/api";
import { cn } from "@/lib/utils";
import { karcodeErrorMessage } from "@/components/module-2/karcode-common";
import { QrScanner } from "@/components/module-2/qr-scanner";

// Longest kar number the keypad accepts (kar numbers are short; the backend
// accepts up to 20 digits).
const MAX_KAR_DIGITS = 10;
// Wait this long after the last key before asking the backend for the code.
const DEBOUNCE_MS = 300;
// How many recent kar -> code pairs are kept (this browser session only).
const MAX_RECENT = 5;
// The "rolling digits" animation when a new code appears.
const SCRAMBLE_TICKS = 8;
const SCRAMBLE_TICK_MS = 45;
// The display always shows at least this many digit cells (unlit "8"s).
const MIN_DISPLAY_CELLS = 4;

interface RecentCode {
  kar: string;
  code: string;
}

// The longest scanned QR text that's passed on (a kar number is short).
const MAX_SCANNED_LENGTH = 20;
// Only the last digits of a scanned QR code are the kar number for the lock
// code (e.g. "K0036" -> "036").
const SCANNED_KAR_DIGITS = 3;

interface KarcodeCalculatorProps {
  /** "desktop": recent list beside the device, keyboard hint, tapping the
   *  display opens the hidden input. "phone": one column, bigger keys, and
   *  the phone's own keyboard never pops up over the keypad. */
  variant: "desktop" | "phone";
}

export function KarcodeCalculator({ variant }: KarcodeCalculatorProps) {
  const isPhone = variant === "phone";
  const t = useTranslations("karTracker.karcodeSimulator");
  const tKarcode = useTranslations("karTracker.karcode");

  // What's typed, the code the backend returned for it, and any error.
  const [kar, setKar] = useState("");
  const [result, setResult] = useState<RecentCode | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [recent, setRecent] = useState<RecentCode[]>([]);
  // Rolling digits shown instead of the code while it "lands" (null = none).
  const [scramble, setScramble] = useState<string | null>(null);
  // The key that lights up when pressed on the physical keyboard.
  const [flashKey, setFlashKey] = useState<string | null>(null);
  // The QR camera panel is open.
  const [isScanning, setIsScanning] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  // Only the answer to the latest request may update the screen.
  const requestIdRef = useRef(0);

  // --- Fetching the code -----------------------------------------------------

  const calculate = useCallback(
    async (karNumber: string) => {
      const requestId = ++requestIdRef.current;
      if (!karNumber) {
        setResult(null);
        setErrorMessage(null);
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      try {
        const answer = await getKarcode(karNumber);
        if (requestId !== requestIdRef.current) return;
        setResult(answer);
        setErrorMessage(null);
        // Remember it; typing on ("3" -> "36") replaces the previous entry.
        setRecent((previous) => {
          const [last, ...older] = previous;
          const kept =
            last && answer.kar.startsWith(last.kar) ? older : previous;
          return [
            answer,
            ...kept.filter((item) => item.kar !== answer.kar),
          ].slice(0, MAX_RECENT);
        });
      } catch (error) {
        if (requestId !== requestIdRef.current) return;
        setResult(null);
        setErrorMessage(karcodeErrorMessage(tKarcode, error));
      } finally {
        if (requestId === requestIdRef.current) setIsLoading(false);
      }
    },
    [tKarcode],
  );

  // Recalculate shortly after the kar number stops changing.
  useEffect(() => {
    const timer = window.setTimeout(() => void calculate(kar), DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [kar, calculate]);

  // Roll the digits for a moment when a new code arrives (skipped when the
  // user asked the system for less motion).
  useEffect(() => {
    const code = result?.code ?? "";
    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (!code || reduceMotion) return;
    let tick = 0;
    const timer = window.setInterval(() => {
      tick += 1;
      if (tick >= SCRAMBLE_TICKS) {
        setScramble(null);
        window.clearInterval(timer);
        return;
      }
      setScramble(
        code.replace(/\d/g, () => String(Math.floor(Math.random() * 10))),
      );
    }, SCRAMBLE_TICK_MS);
    return () => {
      window.clearInterval(timer);
      setScramble(null);
    };
  }, [result]);

  // --- Keypad actions ---------------------------------------------------------

  const pressDigit = useCallback((digit: string) => {
    setKar((previous) =>
      previous.length >= MAX_KAR_DIGITS ? previous : previous + digit,
    );
  }, []);
  const pressBackspace = useCallback(
    () => setKar((previous) => previous.slice(0, -1)),
    [],
  );
  const pressClear = useCallback(() => setKar(""), []);
  const pressEquals = useCallback(() => void calculate(kar), [calculate, kar]);

  // Light up a key briefly (physical keyboard feedback).
  function flash(key: string) {
    setFlashKey(key);
    window.setTimeout(
      () => setFlashKey((current) => (current === key ? null : current)),
      120,
    );
  }

  // The physical keyboard drives the keypad too, unless the focus is in a
  // field (the hidden input handles its own typing).
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, select, [contenteditable]")) return;
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      if (/^\d$/.test(event.key)) {
        pressDigit(event.key);
        flash(event.key);
      } else if (event.key === "Backspace") {
        pressBackspace();
        flash("back");
      } else if (event.key === "Escape" || event.key === "Delete") {
        pressClear();
        flash("clear");
      } else if (event.key === "Enter" || event.key === "=") {
        event.preventDefault();
        pressEquals();
        flash("equals");
      } else {
        return;
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [pressDigit, pressBackspace, pressClear, pressEquals]);

  // A scanned QR code replaces what's typed with its last 3 digits, and the
  // code follows as after typing. A code without any digit is passed on as
  // is, so the display shows the backend's "not a kar number".
  function handleScanned(text: string) {
    setIsScanning(false);
    const digits = text.replace(/\D/g, "");
    setKar(
      digits
        ? digits.slice(-SCANNED_KAR_DIGITS)
        : text.trim().slice(0, MAX_SCANNED_LENGTH),
    );
  }

  async function copyCode() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.code);
      toast.success(t("copied", { code: result.code }));
    } catch {
      toast.error(t("copyFailed"));
    }
  }

  const hasError = errorMessage !== null && kar !== "";
  // The display shows "Err" on an error, else the (rolling) code.
  const displayText = hasError
    ? "Err"
    : kar
      ? (scramble ?? result?.code ?? "")
      : "";
  const cellCount = Math.max(MIN_DISPLAY_CELLS, displayText.length);

  return (
    <>
      <div
        className={cn(
          "flex items-start justify-center",
          isPhone ? "flex-col items-center gap-5" : "flex-wrap gap-8",
        )}
      >
        {/* The calculator's casing (keeps its own dark look in both themes). */}
        <div
          className={cn(
            "w-full rounded-[2rem] bg-gradient-to-b from-zinc-700 via-zinc-800 to-zinc-950 shadow-2xl ring-1 ring-black/40 ring-inset",
            isPhone ? "max-w-sm p-4" : "max-w-[22rem] p-5",
          )}
        >
          {/* Brand strip: lock icon + name, and a little "solar panel". */}
          <div className="mb-4 flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="flex size-8 items-center justify-center rounded-lg bg-purple-600 text-white shadow-md shadow-purple-950/50">
                <LockKeyhole className="size-4" />
              </span>
              <span className="text-sm font-bold tracking-[0.3em] text-zinc-200 uppercase">
                {t("deviceTitle")}
              </span>
            </div>
            <div className="grid h-6 w-24 grid-cols-4 gap-px overflow-hidden rounded-sm bg-zinc-950 p-px shadow-inner">
              {Array.from({ length: 4 }, (_, index) => (
                <span
                  key={index}
                  className="bg-gradient-to-b from-amber-950 to-stone-900"
                />
              ))}
            </div>
          </div>

          {/* The display: on the web, click it to type in the hidden input
              (paste works too); on the phone the keypad is the keyboard. */}
          <div
            className={cn(
              "relative rounded-xl border-4 border-zinc-950 bg-gradient-to-b from-[#1b2012] to-[#0b0e07] px-4 pt-3 pb-4 shadow-[inset_0_4px_14px_rgba(0,0,0,0.85)]",
              !isPhone && "cursor-text",
            )}
            onClick={isPhone ? undefined : () => inputRef.current?.focus()}
          >
            {/* Top line: what's typed, with a blinking cursor. */}
            <div className="flex h-6 items-center justify-between font-mono text-sm text-yellow-300/80">
              <span className="flex items-center gap-2">
                <span className="text-yellow-300/50 uppercase">
                  {t("karLabel")}
                </span>
                <span className="tracking-widest">{kar || " "}</span>
                <span className="inline-block h-4 w-2 animate-pulse bg-yellow-300/70" />
              </span>
              <span className="text-xs text-yellow-300/50">
                {isLoading ? t("calculating") : ""}
              </span>
            </div>

            {/* Main line: the code in seven-segment digits. */}
            <div
              className="mt-2 flex items-center justify-end gap-1.5"
              aria-live="polite"
            >
              <span className="sr-only">
                {hasError ? errorMessage : result ? result.code : t("prompt")}
              </span>
              <SevenSegmentText text={displayText} cells={cellCount} />
            </div>

            {/* Copy the code. */}
            {result && !hasError && (
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  void copyCode();
                }}
                className="absolute bottom-2 left-2 rounded-md p-1.5 text-yellow-300/50 transition-colors hover:bg-yellow-300/10 hover:text-yellow-300"
                aria-label={t("copy")}
                title={t("copy")}
              >
                <Copy className="size-4" />
              </button>
            )}

            {/* Hidden real input: phone keyboard, paste and screen readers. */}
            <input
              ref={inputRef}
              aria-label={t("inputLabel")}
              inputMode="numeric"
              autoComplete="off"
              className="sr-only"
              value={kar}
              onChange={(event) =>
                setKar(
                  event.target.value
                    .replace(/\D/g, "")
                    .slice(0, MAX_KAR_DIGITS),
                )
              }
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  pressEquals();
                } else if (event.key === "Escape") {
                  pressClear();
                }
              }}
            />
          </div>

          {/* Below the display: the prompt, or what went wrong. */}
          <p
            className={cn(
              "mt-2 min-h-10 px-1 text-xs",
              hasError ? "text-rose-300" : "text-zinc-400",
            )}
          >
            {hasError ? errorMessage : t("prompt")}
          </p>

          {/* Scan the QR code on the kar instead of typing its number. */}
          <button
            type="button"
            onClick={() => setIsScanning(true)}
            className="mb-3 flex h-12 w-full items-center justify-center gap-2 rounded-xl border border-purple-400/40 bg-purple-500/15 text-sm font-semibold tracking-wide text-purple-100 transition-colors hover:bg-purple-500/25 focus-visible:ring-2 focus-visible:ring-yellow-300 focus-visible:outline-none active:translate-y-px"
          >
            <ScanLine className="size-5" />
            {t("scanQr")}
          </button>

          {/* The keypad: digits, clear, backspace and a tall "=". */}
          <div className="grid grid-cols-4 gap-3">
            {["7", "8", "9"].map((digit) => (
              <KeypadButton
                big={isPhone}
                key={digit}
                label={digit}
                flashing={flashKey === digit}
                onPress={() => pressDigit(digit)}
              />
            ))}
            <KeypadButton
              big={isPhone}
              label="C"
              tone="danger"
              ariaLabel={t("clear")}
              flashing={flashKey === "clear"}
              onPress={pressClear}
            />
            {["4", "5", "6"].map((digit) => (
              <KeypadButton
                big={isPhone}
                key={digit}
                label={digit}
                flashing={flashKey === digit}
                onPress={() => pressDigit(digit)}
              />
            ))}
            <KeypadButton
              big={isPhone}
              label={<Delete className="size-5" />}
              tone="muted"
              ariaLabel={t("backspace")}
              flashing={flashKey === "back"}
              onPress={pressBackspace}
            />
            {["1", "2", "3"].map((digit) => (
              <KeypadButton
                big={isPhone}
                key={digit}
                label={digit}
                flashing={flashKey === digit}
                onPress={() => pressDigit(digit)}
              />
            ))}
            <KeypadButton
              big={isPhone}
              label="="
              tone="accent"
              ariaLabel={t("calculate")}
              className="row-span-2 h-full"
              flashing={flashKey === "equals"}
              onPress={pressEquals}
            />
            <KeypadButton
              big={isPhone}
              label="0"
              className="col-span-3"
              flashing={flashKey === "0"}
              onPress={() => pressDigit("0")}
            />
          </div>

          {!isPhone && (
            <p className="mt-4 hidden text-center text-[11px] text-zinc-500 md:block">
              {t("keyboardHint")}
            </p>
          )}
        </div>

        {/* Recent calculations (this session only); click one to show it again. */}
        <div
          className={cn(
            "w-full rounded-xl border bg-card p-4",
            isPhone ? "max-w-sm" : "max-w-xs",
          )}
        >
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <History className="size-4 text-purple-600" />
            {t("recent")}
          </div>
          {recent.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("recentEmpty")}</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {recent.map((item) => (
                <li key={item.kar}>
                  <button
                    type="button"
                    onClick={() => setKar(item.kar)}
                    className="flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left transition-colors hover:bg-muted"
                  >
                    <span className="text-sm text-muted-foreground">
                      {t("karLabel")}{" "}
                      <span className="font-semibold text-foreground">
                        {item.kar}
                      </span>
                    </span>
                    <span className="rounded-md bg-zinc-900 px-2 py-0.5 font-mono text-base font-bold tracking-widest text-yellow-300">
                      {item.code}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* The QR camera, full screen over everything; stops when closed. */}
      {isScanning && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-black/90 p-4 pt-[calc(1rem+env(safe-area-inset-top))] pb-[calc(1rem+env(safe-area-inset-bottom))]">
          <div className="relative w-full max-w-sm overflow-hidden rounded-2xl bg-black">
            <QrScanner
              active={isScanning}
              onScanned={handleScanned}
              className="aspect-[3/4] w-full"
            />
            {/* The aiming square in the middle of the camera picture. */}
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div className="size-56 rounded-2xl border-4 border-purple-500" />
            </div>
          </div>
          <p className="text-center text-sm text-zinc-200">{t("scanHint")}</p>
          <button
            type="button"
            onClick={() => setIsScanning(false)}
            className="flex h-12 items-center gap-2 rounded-xl bg-zinc-700 px-6 font-semibold text-white hover:bg-zinc-600"
          >
            <X className="size-5" />
            {t("scanCancel")}
          </button>
        </div>
      )}
    </>
  );
}

// --- Keypad button ------------------------------------------------------------

const KEY_TONES = {
  digit:
    "bg-gradient-to-b from-zinc-600 to-zinc-700 text-zinc-50 shadow-[0_4px_0_0_#18181b]",
  muted:
    "bg-gradient-to-b from-zinc-500 to-zinc-600 text-zinc-50 shadow-[0_4px_0_0_#27272a]",
  danger:
    "bg-gradient-to-b from-rose-500 to-rose-600 text-white shadow-[0_4px_0_0_#881337]",
  accent:
    "bg-gradient-to-b from-purple-500 to-purple-700 text-white shadow-[0_4px_0_0_#3b0764]",
} as const;

interface KeypadButtonProps {
  label: React.ReactNode;
  onPress: () => void;
  tone?: keyof typeof KEY_TONES;
  ariaLabel?: string;
  className?: string;
  // Pressed on the physical keyboard right now: show it pushed in.
  flashing?: boolean;
  // Taller keys for thumbs (phone).
  big?: boolean;
}

function KeypadButton({
  label,
  onPress,
  tone = "digit",
  ariaLabel,
  className,
  flashing,
  big,
}: KeypadButtonProps) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      title={ariaLabel}
      onClick={onPress}
      className={cn(
        "flex items-center justify-center rounded-xl text-2xl font-semibold transition-all duration-75 select-none",
        "hover:brightness-110 focus-visible:ring-2 focus-visible:ring-yellow-300 focus-visible:outline-none",
        "active:translate-y-[3px] active:shadow-[0_1px_0_0_#09090b]",
        big ? "h-16" : "h-14",
        KEY_TONES[tone],
        flashing &&
          "translate-y-[3px] shadow-[0_1px_0_0_#09090b] brightness-125",
        className,
      )}
    >
      {label}
    </button>
  );
}

// --- Seven-segment display -------------------------------------------------------

// The seven segments (a = top, then clockwise, g = middle) of one digit
// cell, drawn in a 60 x 100 box.
const SEGMENTS: Record<string, string> = {
  a: "10,4 50,4 54,8 50,12 10,12 6,8",
  b: "54,10 58,14 58,44 54,48 50,44 50,14",
  c: "54,52 58,56 58,86 54,90 50,86 50,56",
  d: "10,88 50,88 54,92 50,96 10,96 6,92",
  e: "6,52 10,56 10,86 6,90 2,86 2,56",
  f: "6,10 10,14 10,44 6,48 2,44 2,14",
  g: "10,46 50,46 54,50 50,54 10,54 6,50",
};

// Which segments light up per character.
const CHARACTER_SEGMENTS: Record<string, string> = {
  "0": "abcdef",
  "1": "bc",
  "2": "abged",
  "3": "abgcd",
  "4": "fgbc",
  "5": "afgcd",
  "6": "afgedc",
  "7": "abc",
  "8": "abcdefg",
  "9": "abcdfg",
  "-": "g",
  E: "adefg",
  r: "eg",
};

interface SevenSegmentTextProps {
  text: string;
  // Number of digit cells; unused cells on the left stay unlit.
  cells: number;
}

function SevenSegmentText({ text, cells }: SevenSegmentTextProps) {
  // A "." lights the dot of the digit before it instead of taking a cell.
  const characters: { character: string; dot: boolean }[] = [];
  for (const character of text) {
    if (character === "." && characters.length > 0)
      characters[characters.length - 1].dot = true;
    else characters.push({ character, dot: false });
  }
  const padded = [
    ...Array.from({ length: Math.max(0, cells - characters.length) }, () => ({
      character: " ",
      dot: false,
    })),
    ...characters,
  ];
  // Shrink the digits when there are many of them.
  const height = padded.length > 6 ? "h-12" : "h-16 sm:h-20";

  return (
    <div className="flex items-end gap-1.5" aria-hidden>
      {padded.map(({ character, dot }, index) => {
        const lit = CHARACTER_SEGMENTS[character] ?? "";
        return (
          <svg
            key={index}
            viewBox="0 0 68 100"
            className={cn(height, "w-auto -skew-x-6 overflow-visible")}
          >
            {Object.entries(SEGMENTS).map(([segment, points]) => (
              <polygon
                key={segment}
                points={points}
                className={cn(
                  "transition-[fill,opacity] duration-100",
                  lit.includes(segment)
                    ? "fill-yellow-300 drop-shadow-[0_0_6px_rgba(253,224,71,0.75)]"
                    : "fill-yellow-200 opacity-[0.07]",
                )}
              />
            ))}
            <circle
              cx="63"
              cy="92"
              r="4"
              className={
                dot
                  ? "fill-yellow-300 drop-shadow-[0_0_6px_rgba(253,224,71,0.75)]"
                  : "fill-yellow-200 opacity-[0.07]"
              }
            />
          </svg>
        );
      })}
    </div>
  );
}
