/*
 * Quante minuzie trova NBIS in questa immagine?
 *
 * Serve a scegliere l'elaborazione senza rimettere il dito sul sensore a ogni
 * tentativo: si cattura una volta con grab-raw.py e poi si prova qui.
 *
 * Legge un PGM binario (P5), eventualmente lo ingrandisce e/o lo marca come
 * invertito, chiama fp_image_detect_minutiae e stampa quante ne ha trovate.
 *
 * gcc mintest.c -o mintest $(pkg-config --cflags --libs libfprint-2 glib-2.0)
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "fprint.h"
#include "fpi-image.h"

typedef struct
{
  GMainLoop *loop;
  int        count;
  char      *label;
} Ctx;

static void
on_done (GObject *src, GAsyncResult *res, gpointer data)
{
  Ctx *ctx = data;
  FpImage *img = FP_IMAGE (src);
  g_autoptr(GError) error = NULL;

  if (fp_image_detect_minutiae_finish (img, res, &error))
    {
      GPtrArray *m = fp_image_get_minutiae (img);
      ctx->count = m ? (int) m->len : 0;
    }
  else
    {
      ctx->count = -1;
      g_printerr ("  %s: %s\n", ctx->label,
                  error ? error->message : "errore ignoto");
    }

  g_main_loop_quit (ctx->loop);
}

static FpImage *
load_pgm (const char *path)
{
  FILE *f = fopen (path, "rb");
  char magic[3] = { 0 };
  int w, h, maxv;
  FpImage *img;

  if (!f)
    {
      g_printerr ("non apro %s\n", path);
      return NULL;
    }

  if (fscanf (f, "%2s %d %d %d", magic, &w, &h, &maxv) != 4 ||
      strcmp (magic, "P5") != 0)
    {
      g_printerr ("%s non e' un PGM binario\n", path);
      fclose (f);
      return NULL;
    }

  fgetc (f);                            /* il singolo spazio dopo maxval */

  img = fp_image_new (w, h);
  if (fread (img->data, 1, (size_t) w * h, f) != (size_t) w * h)
    {
      g_printerr ("%s: pixel mancanti\n", path);
      g_clear_object (&img);
    }

  fclose (f);

  return img;
}

/*
 * Ingrandimento bilineare. fpi_image_resize e' interno alla libreria e qui non
 * si puo' chiamare, ma per decidere la scala basta questo.
 */
static FpImage *
upscale (FpImage *src, gdouble factor)
{
  guint w = (guint) (src->width * factor + 0.5);
  guint h = (guint) (src->height * factor + 0.5);
  FpImage *dst = fp_image_new (w, h);

  for (guint y = 0; y < h; y++)
    {
      gdouble sy = (y + 0.5) / factor - 0.5;
      gint y0 = (gint) floor (sy);
      gdouble fy = sy - y0;

      gint ya = CLAMP (y0, 0, (gint) src->height - 1);
      gint yb = CLAMP (y0 + 1, 0, (gint) src->height - 1);

      for (guint x = 0; x < w; x++)
        {
          gdouble sx = (x + 0.5) / factor - 0.5;
          gint x0 = (gint) floor (sx);
          gdouble fx = sx - x0;

          gint xa = CLAMP (x0, 0, (gint) src->width - 1);
          gint xb = CLAMP (x0 + 1, 0, (gint) src->width - 1);

          gdouble v =
            src->data[ya * src->width + xa] * (1 - fx) * (1 - fy) +
            src->data[ya * src->width + xb] * fx * (1 - fy) +
            src->data[yb * src->width + xa] * (1 - fx) * fy +
            src->data[yb * src->width + xb] * fx * fy;

          dst->data[y * w + x] = (guint8) CLAMP ((gint) (v + 0.5), 0, 255);
        }
    }

  return dst;
}

static int
try_variant (FpImage *base, gdouble factor, gboolean inverted, const char *label)
{
  g_autoptr(FpImage) img = NULL;
  Ctx ctx = { 0 };

  if (factor != 1.0)
    img = upscale (base, factor);
  else
    img = g_object_ref (base);

  if (inverted)
    img->flags |= FPI_IMAGE_COLORS_INVERTED;

  /* Il sensore ha le creste ogni 8 px: circa 16 pixel per millimetro, dato
     che il passo delle creste umane sta intorno al mezzo millimetro. */
  img->ppmm = 16.0 * factor;

  /* Niente FPI_IMAGE_PARTIAL: quel flag accende remove_perimeter_pts in NBIS,
     che butta via le minuzie vicine al bordo. Su un'immagine di 4 mm per lato
     sono quasi tutte vicine al bordo. */

  ctx.loop = g_main_loop_new (NULL, FALSE);
  ctx.label = (char *) label;
  fp_image_detect_minutiae (img, NULL, on_done, &ctx);
  g_main_loop_run (ctx.loop);
  g_main_loop_unref (ctx.loop);

  g_print ("  %-28s %3dx%-3d  minuzie: %d\n", label, img->width, img->height,
           ctx.count);

  return ctx.count;
}

int
main (int argc, char **argv)
{
  g_autoptr(FpImage) base = NULL;

  if (argc < 2)
    {
      g_printerr ("uso: mintest immagine.pgm\n");
      return 2;
    }

  base = load_pgm (argv[1]);
  if (!base)
    return 1;

  g_print ("%s: %ux%u\n", argv[1], base->width, base->height);

  const gdouble factors[] = { 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0 };

  for (guint i = 0; i < G_N_ELEMENTS (factors); i++)
    {
      char label[64];

      g_snprintf (label, sizeof (label), "scala %.2f, dritta", factors[i]);
      try_variant (base, factors[i], FALSE, label);
      g_snprintf (label, sizeof (label), "scala %.2f, invertita", factors[i]);
      try_variant (base, factors[i], TRUE, label);
    }

  return 0;
}
