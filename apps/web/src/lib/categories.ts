import content from "@/content/categories.json";
import mediaJson from "@/content/category-media.json";

export type Category = (typeof content.categories)[number];

type Img = { url: string; width: number; height: number; alt: string };
export type CategoryMedia = {
  hero?: Img;
  poster?: Img;
  video?: { duration_ms?: number; sources: { url: string; width: number; height: number }[] };
};

export const categories: Category[] = [...content.categories].sort((a, b) => a.step - b.step);

export const getCategory = (slug: string) => categories.find((c) => c.slug === slug);

export const categoryForStep = (step: number) => categories.find((c) => c.step === step);

export const categoryMedia = (slug: string): CategoryMedia => (mediaJson as Record<string, CategoryMedia>)[slug] ?? {};

/** Short labels for navigation (routine order). */
export const NAV_LABELS: Record<string, string> = {
  cleansers: "Cleanse",
  "toners-exfoliants": "Tone",
  serums: "Treat",
  moisturizers: "Moisturize",
  "sun-protection": "Protect",
  masks: "Masks",
};
