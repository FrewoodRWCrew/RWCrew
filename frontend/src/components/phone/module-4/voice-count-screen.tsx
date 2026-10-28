"use client";

// The phone's voice count ("Spraaktelling"), in three steps:
// 1. scan the QR code on a kar (only the kar number; unknown → scan again);
// 2. choose Ophalen or Terugbrengen;
// 3. hold the microphone and say what is there ("twintig rollen tape en 5
//    kabelhaspels"): each sentence becomes lines of product + quantity
//    (voice-count-parser.ts). Lines can be corrected (+/−, other product,
//    delete); an orange line wasn't recognised for sure and needs a tap.
// "Opslaan" stores the count in StockMaster (it doesn't change stock yet)
// and starts again at the scan. Without speech recognition in the browser
// lines can still be added by hand.

import { useMemo, useRef, useState } from "react";
import { ArrowDownToLine, ArrowUpFromLine, Check, Mic, Minus, Plus, Trash2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";
import { createStockMasterVoiceCount } from "@/lib/api";
import type {
  StockMasterVoiceCountDirection,
  StockMasterVoiceCountKar,
  StockMasterVoiceCountLookups,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { QrScanner } from "@/components/module-2/qr-scanner";
import { stockErrorMessage } from "@/components/module-4/stockmaster-common";
import { useSelectedSeason } from "@/components/shared/season-provider";
import { matchProduct, parsePhrase, type MatchConfidence } from "@/components/phone/module-4/voice-count-parser";
import { useSpeechRecognition, type SpeechFailure } from "@/components/phone/module-4/use-speech-recognition";
import { PhoneNotice } from "@/components/phone/shared/phone-notice";
import { PhoneSelect } from "@/components/phone/shared/phone-select";

// How long to wait after an unknown kar code before scanning again.
const RESCAN_DELAY_MS = 1500;
// The "no product chosen" entry of a line's product picker.
const NO_PRODUCT_VALUE = "";
// Speech recognition language per app language.
const SPEECH_LANG: Record<string, string> = { nl: "nl-BE", en: "en-GB" };

/** One line on the screen, before saving. */
interface CountLine {
  /** Stable key for React (lines are added and removed). */
  key: number;
  productId: number | null;
  quantity: number;
  /** What was said for it; null for a line added by hand. */
  spokenText: string | null;
  /** sure = taken as is; doubtful/none = orange until confirmed or picked. */
  confidence: MatchConfidence;
}

/** Kar numbers are compared trimmed and ignoring upper/lower case. */
function normalizeKarNummer(value: string): string {
  return value.trim().toLowerCase();
}

export function VoiceCountScreen({ lookups }: { lookups: StockMasterVoiceCountLookups }) {
  const t = useTranslations("stockMaster.phone.voiceCount");
  const tStock = useTranslations("stockMaster");
  const locale = useLocale();
  const { selectedSeasonId } = useSelectedSeason();

  const [kar, setKar] = useState<StockMasterVoiceCountKar | null>(null);
  const [direction, setDirection] = useState<StockMasterVoiceCountDirection | null>(null);
  const [lines, setLines] = useState<CountLine[]>([]);
  const [isScanning, setIsScanning] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  // The hand-add row (also the fallback without speech recognition).
  const [manualProductId, setManualProductId] = useState(NO_PRODUCT_VALUE);
  const [manualQuantity, setManualQuantity] = useState("1");
  const nextKeyRef = useRef(1);

  const productNames = useMemo(
    () => new Map(lookups.products.map((product) => [product.id, product.name])),
    [lookups.products],
  );

  /** Add lines; a sure line of a product already on the list adds to it. */
  function addLines(newLines: Omit<CountLine, "key">[]) {
    setLines((current) => {
      const result = [...current];
      for (const line of newLines) {
        const existing =
          line.confidence === "sure"
            ? result.find((candidate) => candidate.confidence === "sure" && candidate.productId === line.productId)
            : undefined;
        if (existing) {
          const merged: CountLine = {
            ...existing,
            quantity: existing.quantity + line.quantity,
            spokenText: [existing.spokenText, line.spokenText].filter(Boolean).join(" · ") || null,
          };
          result[result.indexOf(existing)] = merged;
        } else {
          result.push({ ...line, key: nextKeyRef.current++ });
        }
      }
      return result;
    });
  }

  /** A recognised sentence: a command, or new lines. */
  function handleSentence(text: string) {
    const phrase = parsePhrase(text);
    if (phrase.kind === "removeLast") {
      setLines((current) => current.slice(0, -1));
      return;
    }
    if (phrase.pieces.length === 0) {
      toast.warning(t("notUnderstood", { text }));
      return;
    }
    addLines(
      phrase.pieces.map((piece) => {
        const match = matchProduct(piece.words, lookups.products);
        return {
          productId: match.productId,
          quantity: piece.quantity,
          spokenText: piece.spokenText,
          // Without a heard number the quantity is a guess: always check it.
          confidence: piece.quantityGuessed && match.confidence === "sure" ? "doubtful" : match.confidence,
        };
      }),
    );
  }

  function handleSpeechFailure(failure: SpeechFailure) {
    toast.error(t(`speechErrors.${failure}`));
  }

  const speech = useSpeechRecognition({
    lang: SPEECH_LANG[locale] ?? "nl-BE",
    onFinal: handleSentence,
    onFailure: handleSpeechFailure,
  });

  function handleScanned(text: string) {
    setIsScanning(false);
    const found = lookups.kars.find((candidate) => normalizeKarNummer(candidate.kar_nummer) === normalizeKarNummer(text));
    if (found) {
      setKar(found);
      return;
    }
    // Unknown number: say so, then scan again after a short pause.
    toast.error(t("karNotFound", { kar: text.trim() }));
    window.setTimeout(() => setIsScanning(true), RESCAN_DELAY_MS);
  }

  /** Back to the start (after saving, or "Andere kar"). */
  function restart() {
    setKar(null);
    setDirection(null);
    setLines([]);
    setIsScanning(true);
  }

  function updateLine(key: number, change: Partial<CountLine>) {
    setLines((current) => current.map((line) => (line.key === key ? { ...line, ...change } : line)));
  }

  function removeLine(key: number) {
    setLines((current) => current.filter((line) => line.key !== key));
  }

  function addManualLine() {
    const quantity = Number(manualQuantity);
    if (manualProductId === NO_PRODUCT_VALUE || !Number.isInteger(quantity) || quantity < 1) return;
    addLines([{ productId: Number(manualProductId), quantity, spokenText: null, confidence: "sure" }]);
    setManualProductId(NO_PRODUCT_VALUE);
    setManualQuantity("1");
  }

  // Saving needs every line confirmed (no orange left) with a product and a quantity.
  const openLines = lines.filter((line) => line.confidence !== "sure" || line.productId === null).length;
  const canSave = lines.length > 0 && openLines === 0 && !isSaving && selectedSeasonId !== null;

  async function handleSave() {
    if (!kar || !direction || selectedSeasonId === null || !canSave) return;
    setIsSaving(true);
    try {
      await createStockMasterVoiceCount({
        season_id: selectedSeasonId,
        kar_id: kar.id,
        direction,
        lines: lines.map((line) => ({
          product_id: line.productId as number,
          quantity: line.quantity,
          spoken_text: line.spokenText,
        })),
      });
      toast.success(t("saved", { kar: kar.kar_nummer }));
      restart();
    } catch (error) {
      toast.error(stockErrorMessage(tStock, error));
    } finally {
      setIsSaving(false);
    }
  }

  if (selectedSeasonId === null) {
    return <PhoneNotice>{t("noSeason")}</PhoneNotice>;
  }

  // Step 1: scan the kar.
  if (!kar) {
    return (
      <div className="flex flex-col gap-4">
        <div className="relative overflow-hidden rounded-xl bg-black">
          <QrScanner active={isScanning} onScanned={handleScanned} className="aspect-[3/4] w-full" />
          {/* The aiming square in the middle of the camera picture. */}
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="size-56 rounded-2xl border-4 border-primary" />
          </div>
        </div>
        <div className="text-center">
          <p className="font-semibold">{t("scanTitle")}</p>
          <p className="text-sm text-muted-foreground">{t("scanHint")}</p>
        </div>
      </div>
    );
  }

  // Step 2: Ophalen or Terugbrengen.
  if (!direction) {
    return (
      <div className="flex flex-col gap-4">
        <KarBanner karNummer={kar.kar_nummer} onChange={restart} changeLabel={t("otherKar")} />
        <p className="text-center font-semibold">{t("chooseDirection")}</p>
        <DirectionButton icon={ArrowUpFromLine} label={t("directions.pickup")} onClick={() => setDirection("pickup")} />
        <DirectionButton icon={ArrowDownToLine} label={t("directions.return")} onClick={() => setDirection("return")} />
      </div>
    );
  }

  // Step 3: speak and correct the list.
  return (
    <div className="flex flex-col gap-4">
      <KarBanner
        karNummer={kar.kar_nummer}
        directionLabel={t(`directions.${direction}`)}
        onChange={restart}
        changeLabel={t("otherKar")}
      />

      {speech.supported ? (
        <div className="flex flex-col items-center gap-2">
          {/* Hold to talk: pressing starts listening, releasing ends the sentence. */}
          <button
            type="button"
            aria-label={t("holdToTalk")}
            className={cn(
              "flex size-32 touch-none items-center justify-center rounded-full shadow-md select-none",
              speech.listening ? "scale-105 bg-red-600 text-white" : "bg-primary text-primary-foreground",
            )}
            onPointerDown={(event) => {
              event.preventDefault();
              event.currentTarget.setPointerCapture(event.pointerId);
              speech.start();
            }}
            onPointerUp={speech.stop}
            onPointerCancel={speech.stop}
            onContextMenu={(event) => event.preventDefault()}
          >
            <Mic className={cn("size-14", speech.listening && "animate-pulse")} />
          </button>
          <p className="min-h-10 text-center text-sm text-muted-foreground">
            {speech.listening ? speech.interimText || t("listening") : t("holdToTalkHint")}
          </p>
        </div>
      ) : (
        <PhoneNotice>{t("noSpeechSupport")}</PhoneNotice>
      )}

      {/* The recognised lines. */}
      {lines.length === 0 ? (
        <PhoneNotice>{t("noLines")}</PhoneNotice>
      ) : (
        <ul className="flex flex-col gap-2">
          {lines.map((line) => {
            const needsCheck = line.confidence !== "sure" || line.productId === null;
            return (
              <li
                key={line.key}
                className={cn("flex flex-col gap-2 rounded-xl border p-3", needsCheck && "border-orange-500 bg-orange-500/10")}
              >
                {needsCheck ? (
                  <div className="flex items-center gap-2">
                    <PhoneSelect
                      aria-label={t("product")}
                      value={line.productId ?? NO_PRODUCT_VALUE}
                      onChange={(event) =>
                        updateLine(line.key, {
                          productId: event.target.value === NO_PRODUCT_VALUE ? null : Number(event.target.value),
                        })
                      }
                    >
                      <option value={NO_PRODUCT_VALUE}>{t("chooseProduct")}</option>
                      {lookups.products.map((product) => (
                        <option key={product.id} value={product.id}>
                          {product.name}
                        </option>
                      ))}
                    </PhoneSelect>
                    <Button
                      type="button"
                      size="icon"
                      className="size-11 shrink-0"
                      aria-label={t("confirmLine")}
                      disabled={line.productId === null}
                      onClick={() => updateLine(line.key, { confidence: "sure" })}
                    >
                      <Check className="size-5" />
                    </Button>
                  </div>
                ) : (
                  <p className="font-semibold">{productNames.get(line.productId as number)}</p>
                )}
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="size-11"
                    aria-label={t("less")}
                    disabled={line.quantity <= 1}
                    onClick={() => updateLine(line.key, { quantity: line.quantity - 1 })}
                  >
                    <Minus className="size-5" />
                  </Button>
                  <Input
                    type="number"
                    inputMode="numeric"
                    min={1}
                    aria-label={t("quantity")}
                    className="h-11 w-20 text-center text-base"
                    value={line.quantity}
                    onChange={(event) => {
                      const quantity = Number(event.target.value);
                      if (Number.isInteger(quantity) && quantity >= 1) updateLine(line.key, { quantity });
                    }}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="size-11"
                    aria-label={t("more")}
                    onClick={() => updateLine(line.key, { quantity: line.quantity + 1 })}
                  >
                    <Plus className="size-5" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="ml-auto size-11 text-destructive"
                    aria-label={t("removeLine")}
                    onClick={() => removeLine(line.key)}
                  >
                    <Trash2 className="size-5" />
                  </Button>
                </div>
                {line.spokenText && <p className="text-xs text-muted-foreground">“{line.spokenText}”</p>}
              </li>
            );
          })}
        </ul>
      )}

      {/* Add a line by hand. */}
      <div className="flex flex-col gap-2 rounded-xl border border-dashed p-3">
        <Label htmlFor="voice-count-manual-product">{t("addByHand")}</Label>
        <PhoneSelect
          id="voice-count-manual-product"
          value={manualProductId}
          onChange={(event) => setManualProductId(event.target.value)}
        >
          <option value={NO_PRODUCT_VALUE}>{t("chooseProduct")}</option>
          {lookups.products.map((product) => (
            <option key={product.id} value={product.id}>
              {product.name}
            </option>
          ))}
        </PhoneSelect>
        <div className="flex gap-2">
          <Input
            type="number"
            inputMode="numeric"
            min={1}
            aria-label={t("quantity")}
            className="h-11 w-24 text-base"
            value={manualQuantity}
            onChange={(event) => setManualQuantity(event.target.value)}
          />
          <Button
            type="button"
            variant="outline"
            className="h-11 flex-1"
            disabled={manualProductId === NO_PRODUCT_VALUE}
            onClick={addManualLine}
          >
            <Plus className="size-4" />
            {t("add")}
          </Button>
        </div>
      </div>

      {openLines > 0 && <p className="text-center text-sm text-orange-600">{t("checkOrangeLines", { count: openLines })}</p>}
      <Button type="button" className="h-12 text-base" disabled={!canSave} onClick={handleSave}>
        {isSaving ? t("saving") : t("save", { count: lines.reduce((sum, line) => sum + line.quantity, 0) })}
      </Button>
    </div>
  );
}

/** The scanned kar (and chosen direction) at the top, with "Andere kar". */
function KarBanner({
  karNummer,
  directionLabel,
  onChange,
  changeLabel,
}: {
  karNummer: string;
  directionLabel?: string;
  onChange: () => void;
  changeLabel: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border p-3">
      <div className="min-w-0 flex-1">
        <p className="text-lg font-bold">{karNummer}</p>
        {directionLabel && <p className="text-sm text-muted-foreground">{directionLabel}</p>}
      </div>
      <Button type="button" variant="outline" onClick={onChange}>
        {changeLabel}
      </Button>
    </div>
  );
}

/** One of the two big Ophalen / Terugbrengen buttons. */
function DirectionButton({
  icon: Icon,
  label,
  onClick,
}: {
  icon: typeof ArrowUpFromLine;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className="flex h-28 items-center justify-center gap-3 rounded-xl bg-primary text-xl font-semibold text-primary-foreground shadow-sm active:brightness-90"
      onClick={onClick}
    >
      <Icon className="size-8" />
      {label}
    </button>
  );
}
