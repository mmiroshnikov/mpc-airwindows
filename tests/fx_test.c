/* Offline host test for the Galactic effect port (mpc-vst-plugins' tools/host_test.c drives synths only: it passes
 * no input buffers). Linked with wrapper/vst2_wrap.c and the engine under ASan/UBSan by tests/run.sh.
 * Checks: two instances, an impulse grows a reverb tail with no NaN/clipping, dry/wet 0 passes the input through,
 * process() accumulates, and a chunk restores every parameter on another instance. Exit 1 on failure. */
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

static int index_of(const char *key) {
    for (int i = 0; i < NPARAMS; i++)
        if (!strcmp(PARAMS[i].key, key)) return i;
    return -1;
}

/* one host block: in = impulse at frame 0 when impulse != 0, else silence */
static void block(AEffect *a, float impulse, float *L, float *R) {
    float il[N] = {0}, ir[N] = {0}, *in[2] = {il, ir}, *out[2] = {L, R};
    il[0] = ir[0] = impulse;
    a->pr(a, in, out, N);
}

int main(void) {
    AEffect *a = VSTPluginMain(host), *b = VSTPluginMain(host);
    CHECK(a && b && a != b, "two instances");
    if (!a || !b) return 1;
    CHECK(a->magic == 0x56737450 && a->npar == NPARAMS && a->ni == 2 && a->no == 2,
          "magic 'VstP', %d params, 2 in / 2 out, uid %08x", a->npar, a->uid);
    CHECK(a->d(a, 35, 0, 0, 0, 0) == 1, "category Effect");

    for (int i = 0; i < NPARAMS; i++) {
        char d[64] = {0};
        a->d(a, 7, i, 0, d, 0);
        CHECK(fabsf(a->getP(a, i) - PARAMS[i].def) < 1e-3f, "%s default %.2f (\"%s\")", PARAMS[i].key, a->getP(a, i), d);
    }

    int wet = index_of("drywet");
    a->setP(a, wet, 1.0f);
    float L[N], R[N];
    double early = 0, tail = 0, peak = 0;
    int nan = 0;
    for (int k = 0; k < 400; k++) {   /* ~1.2 s */
        block(a, k == 0 ? 0.5f : 0.0f, L, R);
        for (int i = 0; i < N; i++) {
            double e = L[i] * L[i] + R[i] * R[i];
            if (isnan(L[i]) || isnan(R[i])) nan = 1;
            if (fabsf(L[i]) > peak) peak = fabsf(L[i]);
            if (fabsf(R[i]) > peak) peak = fabsf(R[i]);
            if (k < 100) early += e; else tail += e;
        }
    }
    CHECK(!nan, "no NaN");
    CHECK(peak < 1.0, "no clipping (peak %.4f)", peak);
    CHECK(early > 1e-6 && tail > 1e-8, "impulse -> reverb tail (energy %.3g then %.3g)", early, tail);

    b->setP(b, wet, 0.0f);
    double diff = 0;
    for (int k = 0; k < 4; k++) {
        float il[N], ir[N], *in[2] = {il, ir}, *out[2] = {L, R};
        for (int i = 0; i < N; i++) il[i] = ir[i] = 0.25f * sinf((k * N + i) * 0.05f);
        b->pr(b, in, out, N);
        for (int i = 0; i < N; i++) diff += fabs(L[i] - il[i]) + fabs(R[i] - ir[i]);
    }
    CHECK(diff / (4 * N * 2) < 1e-3, "dry/wet 0 passes the input through (mean error %.2g)", diff / (4 * N * 2));

    {
        float il[N] = {0}, ir[N] = {0}, *in[2] = {il, ir}, o1[N], o2[N], *out[2] = {o1, o2};
        int kept = 1;
        for (int i = 0; i < N; i++) o1[i] = o2[i] = 1.0f;
        a->p(a, in, out, N);
        for (int i = 0; i < N; i++) kept &= fabsf(o1[i] - 1.0f) < 0.1f && fabsf(o2[i] - 1.0f) < 0.1f;
        CHECK(kept, "process() accumulates into the output");
    }

    a->setP(a, index_of("replace"), 0.1f);
    a->setP(a, index_of("brightness"), 0.2f);
    a->setP(a, index_of("detune"), 0.3f);
    a->setP(a, index_of("bigness"), 0.4f);
    void *ch = 0;
    intptr_t n = a->d(a, 23, 0, 0, &ch, 0);
    CHECK(n > 0, "chunk saved (%ld bytes: \"%s\")", (long)n, n > 0 ? (char *)ch : "");
    if (n > 0) {
        b->d(b, 24, 0, n, ch, 0);
        int same = 1;
        for (int i = 0; i < NPARAMS; i++) same &= fabsf(a->getP(a, i) - b->getP(b, i)) < 1e-4f;
        CHECK(same, "chunk restores every parameter on instance b");
    }

    a->d(a, 1, 0, 0, 0, 0);
    b->d(b, 1, 0, 0, 0, 0);
    printf("%s\n", fails ? "FAILED" : "PASSED");
    return fails ? 1 : 0;
}
