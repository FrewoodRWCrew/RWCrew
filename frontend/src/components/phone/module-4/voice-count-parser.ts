// Turns what was said on the phone's voice count ("twintig rollen tape en 5
// kabelhaspels") into lines of quantity + product. Pure functions (no React),
// so they're easy to test and reuse:
// - parsePhrase: split one spoken sentence into (quantity, product words)
//   pieces, or recognise a command ("verwijder laatste");
// - matchProduct: find the product whose name best fits the spoken words.
// Works for Dutch and English: the browser's speech recognition mostly gives
// digits, but number words ("drieëntwintig", "twenty five") are read too.

/** One recognised piece of a sentence: how many, and the words for the product. */
export interface ParsedPiece {
  quantity: number;
  /** True when no number was heard (the piece then counts as 1). */
  quantityGuessed: boolean;
  /** The product words, normalised (lowercase, no accents). */
  words: string[];
  /** The original words of this piece, for showing under the line. */
  spokenText: string;
}

/** What one spoken sentence means. */
export type ParsedPhrase = { kind: "pieces"; pieces: ParsedPiece[] } | { kind: "removeLast" };

/** How sure a product match is: sure = taken as is, doubtful = needs a tap, none = pick by hand. */
export type MatchConfidence = "sure" | "doubtful" | "none";

export interface ProductMatch {
  productId: number | null;
  confidence: MatchConfidence;
}

interface NamedProduct {
  id: number;
  name: string;
}

// Scores (0..1) above which a match is taken as is / offered as a suggestion.
const SURE_SCORE = 0.8;
const DOUBTFUL_SCORE = 0.5;
// The best two products closer than this are too close to call: doubtful.
const AMBIGUOUS_GAP = 0.08;

// Words that mean nothing for the product ("and", "pieces", packaging units ...).
const FILLER_WORDS = new Set([
  "en", "plus", "stuks", "stuk", "keer", "x", "maal", "van", "de", "het", "nog",
  "rol", "rollen", "doos", "dozen", "pak", "pakken",
  "and", "pieces", "piece", "pcs", "times", "of", "the", "more", "roll", "rolls", "box", "boxes", "pack", "packs",
]);

// Commands that remove the last line again.
const REMOVE_LAST_PHRASES = ["verwijder laatste", "wis laatste", "laatste verwijderen", "delete last", "remove last", "undo"];

// Dutch and English number words (after removing accents: "één" → "een").
const NUMBER_WORDS: Record<string, number> = {
  nul: 0, een: 1, twee: 2, drie: 3, vier: 4, vijf: 5, zes: 6, zeven: 7, acht: 8, negen: 9, tien: 10,
  elf: 11, twaalf: 12, dertien: 13, veertien: 14, vijftien: 15, zestien: 16, zeventien: 17, achttien: 18,
  negentien: 19, twintig: 20, dertig: 30, veertig: 40, vijftig: 50, zestig: 60, zeventig: 70, tachtig: 80,
  negentig: 90, honderd: 100,
  zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18,
  nineteen: 19, twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90,
  hundred: 100,
};

/** Lowercase, accents removed, only letters/digits separated by single spaces. */
export function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/** The value of one number word or digits, or null when it isn't a number.
 *  Also reads Dutch compounds: "drieentwintig" (3 + 20), "tweehonderdvijf". */
export function wordToNumber(word: string): number | null {
  if (/^\d+$/.test(word)) return Number(word);
  if (word in NUMBER_WORDS) return NUMBER_WORDS[word];

  // "[x]honderd[rest]", e.g. "honderdtwintig", "tweehonderd".
  const hundred = /^(\w*?)honderd(\w*)$/.exec(word);
  if (hundred) {
    const times = hundred[1] ? wordToNumber(hundred[1]) : 1;
    const rest = hundred[2] ? wordToNumber(hundred[2].replace(/^en/, "")) : 0;
    if (times !== null && rest !== null && times >= 1 && times < 10 && rest < 100) return times * 100 + rest;
    return null;
  }

  // "<unit>en<tens>", e.g. "eenentwintig", "drieenveertig".
  const compound = /^(\w+?)en(twintig|dertig|veertig|vijftig|zestig|zeventig|tachtig|negentig)$/.exec(word);
  if (compound) {
    const unit = NUMBER_WORDS[compound[1]];
    if (unit !== undefined && unit >= 1 && unit <= 9) return unit + NUMBER_WORDS[compound[2]];
  }
  return null;
}

/** Read a run of number tokens starting at `start` ("twenty five", "two hundred"):
 *  its value and how many tokens it used, or null when there's no number there. */
function readNumber(tokens: string[], start: number): { value: number; used: number } | null {
  const first = wordToNumber(tokens[start]);
  if (first === null) return null;
  let value = first;
  let used = 1;
  while (start + used < tokens.length) {
    const next = wordToNumber(tokens[start + used]);
    if (next === null) break;
    if (next === 100 && value >= 1 && value < 10) {
      value *= 100; // "two hundred"
    } else if (value >= 20 && value % 10 === 0 && value < 100 && next >= 1 && next <= 9) {
      value += next; // "twenty five"
    } else if (value >= 100 && value % 100 === 0 && next >= 1 && next < 100) {
      value += next; // "two hundred five"
    } else {
      break; // two separate numbers
    }
    used += 1;
  }
  return { value, used };
}

/** Split one spoken sentence into pieces, each starting at a number:
 *  "20 rollen tape en 5 kabelhaspels" → (20, rollen tape) + (5, kabelhaspels).
 *  Words before the first number belong to it when it has none of its own
 *  ("tape twintig"); a sentence without numbers is one piece of 1. */
export function parsePhrase(text: string): ParsedPhrase {
  const normalized = normalize(text);
  if (REMOVE_LAST_PHRASES.some((command) => normalized === command)) {
    return { kind: "removeLast" };
  }

  const tokens = normalized.split(" ").filter(Boolean);
  const pieces: { quantity: number | null; tokens: string[] }[] = [];
  let leading: string[] = [];
  let index = 0;
  while (index < tokens.length) {
    const number = readNumber(tokens, index);
    if (number) {
      pieces.push({ quantity: number.value, tokens: [] });
      index += number.used;
      continue;
    }
    const current = pieces.at(-1);
    if (current) current.tokens.push(tokens[index]);
    else leading.push(tokens[index]);
    index += 1;
  }

  // Leading words: to the first number if it has no words, else a piece of their own.
  if (leading.length > 0) {
    if (pieces.length > 0 && pieces[0].tokens.every((token) => FILLER_WORDS.has(token))) {
      pieces[0].tokens = leading;
    } else {
      pieces.unshift({ quantity: null, tokens: leading });
    }
    leading = [];
  }

  const result: ParsedPiece[] = [];
  for (const piece of pieces) {
    const words = piece.tokens.filter((token) => !FILLER_WORDS.has(token));
    // A number without any product words is noise (e.g. a stray "en 3").
    if (words.length === 0) continue;
    const quantity = piece.quantity ?? 1;
    if (quantity < 1) continue;
    result.push({
      quantity,
      quantityGuessed: piece.quantity === null,
      words,
      spokenText: [piece.quantity ?? "", ...piece.tokens].join(" ").trim(),
    });
  }
  return { kind: "pieces", pieces: result };
}

/** A word's simple stem: Dutch/English plurals removed ("rollen" → "rol"). */
function stem(word: string): string {
  if (word.length > 5 && word.endsWith("en")) return word.slice(0, -2).replace(/(.)\1$/, "$1");
  if (word.length > 3 && word.endsWith("s")) return word.slice(0, -1);
  return word;
}

/** Edit distance between two short words. */
function levenshtein(a: string, b: string): number {
  const previous = Array.from({ length: b.length + 1 }, (_, index) => index);
  for (let i = 1; i <= a.length; i += 1) {
    let diagonal = previous[0];
    previous[0] = i;
    for (let j = 1; j <= b.length; j += 1) {
      const above = previous[j];
      previous[j] = Math.min(previous[j] + 1, previous[j - 1] + 1, diagonal + (a[i - 1] === b[j - 1] ? 0 : 1));
      diagonal = above;
    }
  }
  return previous[b.length];
}

/** How alike two (stemmed) words are, 0..1; one inside the other counts high. */
function wordSimilarity(a: string, b: string): number {
  if (a === b) return 1;
  if (a.length >= 3 && b.length >= 3 && (a.includes(b) || b.includes(a))) return 0.9;
  return 1 - levenshtein(a, b) / Math.max(a.length, b.length);
}

/** How well the spoken words fit one product name, 0..1: mostly how well each
 *  spoken word is found in the name, a little how much of the name was said. */
function scoreProduct(spoken: string[], productWords: string[]): number {
  if (spoken.length === 0 || productWords.length === 0) return 0;
  // Joined forms too, so "kabel haspel" also fits "kabelhaspel" and back.
  const candidates = [...productWords, productWords.join("")];
  const spokenCandidates = [...spoken, spoken.join("")];

  const spokenFit =
    spoken.reduce((sum, word) => sum + Math.max(...candidates.map((candidate) => wordSimilarity(word, candidate))), 0) /
    spoken.length;
  const coverage =
    productWords.filter((word) => spokenCandidates.some((candidate) => wordSimilarity(word, candidate) >= 0.8)).length /
    productWords.length;
  return 0.75 * spokenFit + 0.25 * coverage;
}

/** The product that best fits the spoken words, with how sure the match is. */
export function matchProduct(words: string[], products: NamedProduct[]): ProductMatch {
  const spoken = words.map(stem);
  let best: { id: number; score: number } | null = null;
  let secondScore = 0;
  for (const product of products) {
    const productWords = normalize(product.name).split(" ").filter(Boolean).map(stem);
    const score = scoreProduct(spoken, productWords);
    if (!best || score > best.score) {
      secondScore = best?.score ?? 0;
      best = { id: product.id, score };
    } else if (score > secondScore) {
      secondScore = score;
    }
  }

  if (!best || best.score < DOUBTFUL_SCORE) return { productId: null, confidence: "none" };
  const ambiguous = best.score - secondScore < AMBIGUOUS_GAP;
  return { productId: best.id, confidence: best.score >= SURE_SCORE && !ambiguous ? "sure" : "doubtful" };
}
