/*
 * Il confronto scritto in C dice le stesse cose di quello scritto in Python?
 *
 * Il driver rifa' da capo, in C, quello che analisi.py aveva misurato: media
 * dei fotogrammi, differenza di gaussiane, quantizzazione a byte, correlazione
 * su tutti gli scorrimenti. Ognuno di quei passaggi puo' essere sbagliato in un
 * modo che non fa rumore - un segno, un indice, un arrotondamento - e il
 * risultato sarebbe soltanto un sensore che non riconosce nessuno.
 *
 * Qui si rileggono le stesse catture di set-*.bin e si stampano gli stessi
 * punteggi, cosi' i due numeri si possono mettere accanto.
 *
 * Il file del driver si include per intero perche' le funzioni di calcolo sono
 * static: e' l'unico modo di provare esattamente il codice che gira, invece di
 * una copia che potrebbe divergere.
 */

#include "drivers/egis057e.c"

#include <stdio.h>

#define NDITA 5
static const char *DITA[NDITA] = {
  "indice-dx", "medio-dx", "anulare-dx", "pollice-dx", "indice-sx"
};

/*
 * fp-context.c chiede l'elenco dei driver, che sta nell'archivio dei driver.
 * Quello qui non si puo' linkare - contiene gia' egis057e.c, che matchtest
 * include, e il tipo GObject risulterebbe definito due volte - e non serve,
 * perche' nessun contesto viene mai creato: si usano solo make_template e
 * correlate.
 */
GArray *fpi_get_driver_types (void);

GArray *
fpi_get_driver_types (void)
{
  return g_array_new (FALSE, FALSE, sizeof (GType));
}

static gdouble sfondo[EGIS057E_IMGSIZE];

static guint8 *
leggi (const char *nome, gsize *nframes)
{
  gchar *dati = NULL;
  gsize len = 0;

  if (!g_file_get_contents (nome, &dati, &len, NULL))
    {
      g_printerr ("non leggo %s\n", nome);
      return NULL;
    }

  *nframes = len / EGIS057E_IMGSIZE;

  return (guint8 *) dati;
}

/* Stessa scelta di analisi.py: si tengono solo i fotogrammi in cui il dito
   c'e' davvero, con la stessa soglia. */
static gboolean
col_dito (const guint8 *f)
{
  gdouble s = 0;

  for (gint i = 0; i < EGIS057E_IMGSIZE; i++)
    s += fabs ((gdouble) f[i] - sfondo[i]);

  return s / EGIS057E_IMGSIZE > 25.0;
}

/* k modelli distribuiti lungo l'appoggio, ognuno media di EGIS057E_AVG_FRAMES
   fotogrammi consecutivi. */
static GPtrArray *
modelli (const char *dito, int n, int k)
{
  g_autofree gchar *nome = g_strdup_printf ("set-%s-%d.bin", dito, n);
  gsize nf = 0;
  g_autofree guint8 *dati = leggi (nome, &nf);
  GPtrArray *out = g_ptr_array_new_with_free_func (g_free);
  GPtrArray *vivi = g_ptr_array_new ();

  if (!dati)
    return out;

  for (gsize i = 0; i < nf; i++)
    if (col_dito (dati + i * EGIS057E_IMGSIZE))
      g_ptr_array_add (vivi, dati + i * EGIS057E_IMGSIZE);

  for (int j = 0; j < k; j++)
    {
      gdouble avg[EGIS057E_IMGSIZE] = { 0 };
      gint8 *tpl = g_new (gint8, EGIS057E_IMGSIZE);
      gsize base;

      if (vivi->len < EGIS057E_AVG_FRAMES)
        break;

      base = (k == 1) ? 0 :
             (gsize) ((vivi->len - EGIS057E_AVG_FRAMES) * j / (k - 1));

      for (int f = 0; f < EGIS057E_AVG_FRAMES; f++)
        {
          const guint8 *p = g_ptr_array_index (vivi, base + f);
          for (gint i = 0; i < EGIS057E_IMGSIZE; i++)
            avg[i] += p[i] - sfondo[i];
        }
      for (gint i = 0; i < EGIS057E_IMGSIZE; i++)
        avg[i] /= EGIS057E_AVG_FRAMES;

      make_template (avg, tpl);
      g_ptr_array_add (out, tpl);
    }

  g_ptr_array_unref (vivi);

  return out;
}

static gdouble
punteggio (GPtrArray *prove, GPtrArray *iscritti)
{
  gdouble best = -1.0;

  for (guint p = 0; p < prove->len; p++)
    for (guint m = 0; m < iscritti->len; m++)
      {
        gdouble v = correlate (g_ptr_array_index (prove, p),
                               g_ptr_array_index (iscritti, m));
        if (v > best)
          best = v;
      }

  return best;
}

int
main (void)
{
  GPtrArray *isc[NDITA], *pro[NDITA];
  gdouble gmin = 2, gsum = 0, imax = -2;
  gsize nf = 0;
  g_autofree guint8 *bgdati = leggi ("set-fondo.bin", &nf);

  if (!bgdati)
    return 1;

  for (gint i = 0; i < EGIS057E_IMGSIZE; i++)
    sfondo[i] = bgdati[i];

  for (int d = 0; d < NDITA; d++)
    {
      GPtrArray *a = modelli (DITA[d], 1, 8);
      GPtrArray *b = modelli (DITA[d], 2, 8);

      for (guint i = 0; i < b->len; i++)
        g_ptr_array_add (a, g_memdup2 (g_ptr_array_index (b, i),
                                       EGIS057E_IMGSIZE));
      g_ptr_array_unref (b);

      isc[d] = a;
      pro[d] = modelli (DITA[d], 3, 3);
      g_print ("%-12s modelli %2u   prove %u\n", DITA[d], isc[d]->len,
               pro[d]->len);
    }

  g_print ("\npunteggi (riga = iscritto, colonna = presentato)\n\n%14s", "");
  for (int d = 0; d < NDITA; d++)
    g_print ("%11.9s", DITA[d]);
  g_print ("\n");

  for (int a = 0; a < NDITA; a++)
    {
      g_print ("%-14s", DITA[a]);
      for (int b = 0; b < NDITA; b++)
        {
          gdouble s = punteggio (pro[b], isc[a]);

          g_print ("%11.3f", s);
          if (a == b)
            {
              gsum += s;
              if (s < gmin)
                gmin = s;
            }
          else if (s > imax)
            {
              imax = s;
            }
        }
      g_print ("\n");
    }

  g_print ("\ngenuini   min %.3f  media %.3f\n", gmin, gsum / NDITA);
  g_print ("impostori max %.3f\n", imax);
  g_print ("soglia del driver %.2f -> %s\n", EGIS057E_MATCH_THRESHOLD,
           imax < EGIS057E_MATCH_THRESHOLD ? "nessun falso accesso" :
           "FALSI ACCESSI");

  return 0;
}
