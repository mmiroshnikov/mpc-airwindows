/* Offline host test for any Airwindows effect port (tests/run_aw.sh builds it once per port, under ASan/UBSan).
 * Checks: two instances, effect category, defaults match params.json, a quiet signal plus an impulse comes out
 * finite (and below full scale) with every knob at its default and at its minimum, finite at its maximum, process()
 * accumulates, and a chunk restores every parameter on another instance. Exit 1 on failure. */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "params.h"

typedef struct AEffect AEffect;
typedef intptr_t (*cb)(AEffect *, int32_t, int32_t, intptr_t, void *, float);
struct AEffect {
    int32_t magic;
    intptr_t (*d)(AEffect *, int32_t, int32_t, intptr_t, void *, float);
    void (*p)(AEffect *, float **, float **, int32_t);
    void (*setP)(AEffect *, int32_t, float);
    float (*getP)(AEffect *, int32_t);
    int32_t np, npar, ni, no, flags;
    intptr_t r1, r2;
    int32_t a, b, c;
    float io;
    void *obj, *user;
    int32_t uid, ver;
    void (*pr)(AEffect *, float **, float **, int32_t);
    void *pdr;
    char f[56];
};
extern AEffect *VSTPluginMain(cb);

static intptr_t host(AEffect *e, int32_t op, int32_t i, intptr_t v, void *p, float o) { return 0; }

static int fails;
#define CHECK(c, ...) do { printf("%s ", (c) ? "ok  " : "FAIL"); printf(__VA_ARGS__); printf("\n"); if (!(c)) fails++; } while (0)

enum { N = 128 };

/* ~1 s of a quiet 220 Hz sine with an impulse at the start; returns rms, sets *peak */
static double play(AEffect *a, double *peak) {
    float il[N], ir[N], L[N], R[N], *in[2] = {il, ir}, *out[2] = {L, R};
    double e = 0;
    *peak = 0;
    for (int k = 0; k < 344; k++) {
        for (int i = 0; i < N; i++) il[i] = ir[i] = 0.1f * sinf((k * N + i) * 2.0f * 3.14159265f * 220.0f / 44100.0f);
        if (k == 0) il[0] = ir[0] = 0.5f;
        a->pr(a, in, out, N);
        for (int i = 0; i < N; i++) {
            if (!isfinite(L[i]) || !isfinite(R[i])) { *peak = INFINITY; return 0; }
            e += L[i] * L[i] + R[i] * R[i];
            if (fabsf(L[i]) > *peak) *peak = fabsf(L[i]);
            if (fabsf(R[i]) > *peak) *peak = fabsf(R[i]);
        }
    }
    return sqrt(e / (344.0 * N * 2));
}

int main(void) {
    AEffect *a = VSTPluginMain(host), *b = VSTPluginMain(host);
    CHECK(a && b && a != b, "two instances");
    if (!a || !b) return 1;
    CHECK(a->magic == 0x56737450 && a->npar == NPARAMS && a->ni == 2 && a->no == 2 && a->d(a, 35, 0, 0, 0, 0) == 1,
          "%s: effect, %d params, 2 in / 2 out", PLUG_NAME, a->npar);

    int defaults_ok = 1;
    for (int i = 0; i < NPARAMS; i++) defaults_ok &= fabsf(a->getP(a, i) - PARAMS[i].def) < 1e-3f;
    CHECK(defaults_ok, "defaults match params.json");

    const char *label[] = {"defaults", "all knobs min", "all knobs max"};
    for (int pass = 0; pass < 3; pass++) {
        AEffect *t = VSTPluginMain(host);
        if (pass) for (int i = 0; i < NPARAMS; i++) t->setP(t, i, pass == 1 ? 0.0f : 1.0f);
        double peak, rms = play(t, &peak);
        /* at max, Output/Drive/Input knobs are real gain: clipping there is the plugin, not a fault */
        CHECK(isfinite(peak) && (pass == 2 || peak < 0.999), "%s: finite%s (rms %.4f, peak %.4f)", label[pass],
              pass == 2 ? "" : ", below full scale", rms, peak);
        if (pass == 0 && rms < 1e-5) printf("warn defaults: almost silent (rms %.2g)\n", rms);
        t->d(t, 1, 0, 0, 0, 0);
    }

    {
        float il[N] = {0}, ir[N] = {0}, *in[2] = {il, ir}, o1[N], o2[N], *out[2] = {o1, o2};
        int kept = 1;
        for (int i = 0; i < N; i++) o1[i] = o2[i] = 1.0f;
        b->p(b, in, out, N);
        for (int i = 0; i < N; i++) kept &= isfinite(o1[i]) && fabsf(o1[i] - 1.0f) < 0.5f && fabsf(o2[i] - 1.0f) < 0.5f;
        CHECK(kept, "process() accumulates into the output");
    }

    for (int i = 0; i < NPARAMS; i++) a->setP(a, i, (float)(i + 1) / (NPARAMS + 2));
    void *ch = 0;
    intptr_t n = a->d(a, 23, 0, 0, &ch, 0);
    CHECK(n > 0, "chunk saved (%ld bytes)", (long)n);
    if (n > 0) {
        b->d(b, 24, 0, n, ch, 0);
        int same = 1;
        for (int i = 0; i < NPARAMS; i++) same &= fabsf(a->getP(a, i) - b->getP(b, i)) < 1e-4f;
        CHECK(same, "chunk restores every parameter on instance b");
    }

    a->d(a, 1, 0, 0, 0, 0);
    b->d(b, 1, 0, 0, 0, 0);
    printf("%s %s\n", PLUG_NAME, fails ? "FAILED" : "PASSED");
    return fails ? 1 : 0;
}
