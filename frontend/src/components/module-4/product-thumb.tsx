// A product's small picture, as used in StockMaster's webshop-style lists
// (booking basket, kar needs). Products without a picture get a placeholder
// icon in the same square, so every row stays aligned.

import { Package } from "lucide-react";
import { stockMasterProductImageUrl } from "@/lib/api";
import type { StockMasterProductStock } from "@/lib/types";

interface ProductThumbProps {
  productId: number;
  name: string;
  /** The product's stock row (for has_image / image_updated_at); undefined while loading. */
  product: StockMasterProductStock | undefined;
  /** Builds the picture's URL; StockMaster's own endpoint by default (Altsien
   *  Select passes its own, since its users may not have StockMaster access). */
  imageUrl?: (productId: number, updatedAt: string | null) => string;
}

export function ProductThumb({ productId, name, product, imageUrl = stockMasterProductImageUrl }: ProductThumbProps) {
  return (
    <div className="flex size-10 shrink-0 items-center justify-center overflow-hidden rounded-md border bg-muted/40">
      {product?.has_image ? (
        // eslint-disable-next-line @next/next/no-img-element -- authenticated API image, not a static asset
        <img
          src={imageUrl(productId, product.image_updated_at)}
          alt={name}
          loading="lazy"
          className="size-full object-contain"
        />
      ) : (
        <Package className="size-4 text-muted-foreground" />
      )}
    </div>
  );
}
