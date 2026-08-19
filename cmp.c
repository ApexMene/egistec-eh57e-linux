/*
 * Confronto vero fra impronte: bozorth3 su tutte le coppie.
 *
 * Contare le minuzie non dimostra niente. La prova che il sensore serva a
 * qualcosa e' che due passate dello stesso dito diano un punteggio alto e due
 * passate di dita diverse un punteggio basso, con un margine largo in mezzo.
 * Soglia di riferimento di libfprint: 40 (fpi-image-device.h).
 *
 * I simboli interni della libreria sono nascosti dal version script, quindi
 * bozorth3 si compila qui dentro dai sorgenti; le minuzie invece arrivano
 * dall'API pubblica fp_image_detect_minutiae.
 *
 * uso: ./cmp [--scala N] a.pgm b.pgm c.pgm ...
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "fprint.h"
#include "fpi-image.h"

#include "lfs.h"
#include "bozorth.h"

#define MAXIMG 16

typedef struct
{
  GMainLoop *loop;
  GPtrArray *minutiae;
} Ctx;

static void
on_done (GObject *src, GAsyncResult *res, gpointer data)
{
  Ctx *ctx = data;
  FpImage *img = FP_IMAGE (src);
  g_autoptr(GError) error = NULL;

  if (fp_image_detect_minutiae_finish (img, res, &error))
    ctx->minutiae = fp_image_get_minutiae (img);
  else
    g_printerr ("  minuzie non estratte: %s\n",
                error ? error->message : "errore ignoto");

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

/* Stessa bilineare di mintest.c: fpi_image_resize e' interna e non si chiama
   da fuori. */
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

/* Copia di lfs2nist_minutia_XYT (nbis/mindtct/xytreps.c): origine in basso a
   sinistra, angolo in gradi antiorari con lo zero a est e la punta rivolta
   fuori dalla cresta. */
static void
lfs2nist (int *ox, int *oy, int *ot, const MINUTIA *m, int ih)
{
  float degrees_per_unit = 180.0f / (float) NUM_DIRECTIONS;
  int t = (270 - (int) lrintf (m->direction * degrees_per_unit)) % 360;

  if (t < 0)
    t += 360;

  *ox = m->x;
  *oy = ih - m->y;
  *ot = t;
}

/* Copia di minutiae_to_xyt (fpi-print.c): stesso ordinamento, stesso taglio a
   MAX_BOZORTH_MINUTIAE, altrimenti i punteggi non sarebbero confrontabili con
   quelli che produrra' il driver dentro libfprint. */
static void
to_xyt (GPtrArray *minutiae, int ih, struct xyt_struct *xyt)
{
  struct minutiae_struct c[MAX_FILE_MINUTIAE];
  int nmin = (int) minutiae->len;

  if (nmin > MAX_BOZORTH_MINUTIAE)
    nmin = MAX_BOZORTH_MINUTIAE;

  for (int i = 0; i < nmin; i++)
    {
      MINUTIA *m = g_ptr_array_index (minutiae, i);

      lfs2nist (&c[i].col[0], &c[i].col[1], &c[i].col[2], m, ih);
      c[i].col[3] = (int) lrint (m->reliability * 100.0);

      if (c[i].col[2] > 180)
        c[i].col[2] -= 360;
    }

  qsort ((void *) &c, (size_t) nmin, sizeof (struct minutiae_struct), sort_x_y);

  for (int i = 0; i < nmin; i++)
    {
      xyt->xcol[i] = c[i].col[0];
      xyt->ycol[i] = c[i].col[1];
      xyt->thetacol[i] = c[i].col[2];
    }
  xyt->nrows = nmin;
}

int
main (int argc, char **argv)
{
  gdouble scala = 1.25;
  const char *nomi[MAXIMG];
  struct xyt_struct xyt[MAXIMG];
  int n = 0;
  int i = 1;

  if (argc > 2 && strcmp (argv[1], "--scala") == 0)
    {
      scala = g_ascii_strtod (argv[2], NULL);
      i = 3;
    }

  for (; i < argc && n < MAXIMG; i++)
    nomi[n++] = argv[i];

  if (n < 2)
    {
      g_printerr ("uso: cmp [--scala N] a.pgm b.pgm [c.pgm ...]\n");
      return 2;
    }

  g_print ("scala %.2f\n\n", scala);

  for (int k = 0; k < n; k++)
    {
      g_autoptr(FpImage) base = load_pgm (nomi[k]);
      g_autoptr(FpImage) img = NULL;
      Ctx ctx = { 0 };

      if (!base)
        return 1;

      img = (scala != 1.0) ? upscale (base, scala) : g_object_ref (base);
      img->ppmm = 16.0 * scala;

      ctx.loop = g_main_loop_new (NULL, FALSE);
      fp_image_detect_minutiae (img, NULL, on_done, &ctx);
      g_main_loop_run (ctx.loop);
      g_main_loop_unref (ctx.loop);

      memset (&xyt[k], 0, sizeof (xyt[k]));
      if (ctx.minutiae)
        to_xyt (ctx.minutiae, (int) img->height, &xyt[k]);

      g_print ("%-16s %4ux%-4u  minuzie: %d\n", nomi[k], img->width,
               img->height, xyt[k].nrows);
    }

  g_print ("\npunteggi bozorth3 (soglia libfprint: 40)\n\n%18s", "");
  for (int k = 0; k < n; k++)
    g_print ("%10s", nomi[k]);
  g_print ("\n");

  /* bozorth_main e' solo dichiarato in bozorth.h, non definito: la coppia
     probe_init + to_gallery e' quella che usa davvero libfprint. */
  for (int a = 0; a < n; a++)
    {
      int probe_len = bozorth_probe_init (&xyt[a]);

      g_print ("%18s", nomi[a]);
      for (int b = 0; b < n; b++)
        {
          if (a == b)
            g_print ("%10s", "-");
          else
            g_print ("%10d", bozorth_to_gallery (probe_len, &xyt[a], &xyt[b]));
        }
      g_print ("\n");
    }

  return 0;
}
