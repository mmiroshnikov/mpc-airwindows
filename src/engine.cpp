/* Airwindows Galactic as an mpc-vst-plugins effect engine: int16 stereo blocks in, int16 stereo blocks out.
 * Parameters are 0..100 % on the MPC side and 0..1 inside Galactic. */
#include <new>
#include "Galactic.h"

extern "C" {
/* must match mpc-vst-plugins wrapper/engine.h */
typedef struct {
    void *(*create)(const char *data_dir);
    void (*destroy)(void *inst);
    void (*midi)(void *inst, const uint8_t *msg, int len);
    void (*set_param)(void *inst, const char *key, const char *val);
    int (*get_param)(void *inst, const char *key, char *buf, int buf_len);
    void (*render)(void *inst, int16_t *out_lr, int frames);
    void (*process)(void *inst, const int16_t *in_lr, int16_t *out_lr, int frames);
} mpc_engine_t;
const mpc_engine_t *mpc_engine(void);
}

namespace {

const char *const KEYS[kNumParameters] = {"replace", "brightness", "detune", "bigness", "drywet"};
const int MAX_FRAMES = 128;

struct Inst {
    Galactic fx{nullptr};
    float in[2][MAX_FRAMES], out[2][MAX_FRAMES];
};

int key_index(const char *key) {
    for (int i = 0; i < kNumParameters; i++)
        if (!strcmp(key, KEYS[i])) return i;
    return -1;
}

float clamp01(float v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

/* must match the defaults in vst/params.json: the wrapper reads the DSP's values, it never pushes defaults */
const float DEFAULTS[kNumParameters] = {0.5f, 0.5f, 0.5f, 1.0f, 0.3f};

void *create(const char *) {
    Inst *s = new (std::nothrow) Inst;
    if (s)
        for (int i = 0; i < kNumParameters; i++) s->fx.setParameter(i, DEFAULTS[i]);
    return s;
}

void destroy(void *p) { delete static_cast<Inst *>(p); }

void midi(void *, const uint8_t *, int) {}

void set_param(void *p, const char *key, const char *val) {
    Inst *s = static_cast<Inst *>(p);
    if (!strcmp(key, "state")) {
        float v[kNumParameters];
        if (sscanf(val, "%f %f %f %f %f", &v[0], &v[1], &v[2], &v[3], &v[4]) == kNumParameters)
            for (int i = 0; i < kNumParameters; i++) s->fx.setParameter(i, clamp01(v[i]));
        return;
    }
    int i = key_index(key);
    if (i >= 0) s->fx.setParameter(i, clamp01((float)atof(val) / 100.0f));
}

int get_param(void *p, const char *key, char *buf, int len) {
    Inst *s = static_cast<Inst *>(p);
    if (!strcmp(key, "state")) {
        return snprintf(buf, len, "%.6f %.6f %.6f %.6f %.6f", s->fx.getParameter(0), s->fx.getParameter(1),
                        s->fx.getParameter(2), s->fx.getParameter(3), s->fx.getParameter(4));
    }
    int i = key_index(key);
    if (i < 0) return 0;
    return snprintf(buf, len, "%g", s->fx.getParameter(i) * 100.0f);
}

void render(void *, int16_t *out, int frames) { memset(out, 0, sizeof(int16_t) * 2 * frames); }

int16_t to_s16(float f) {
    f *= 32768.0f;
    return f >= 32767.0f ? 32767 : f <= -32768.0f ? -32768 : (int16_t)lrintf(f);
}

void process(void *p, const int16_t *in, int16_t *out, int frames) {
    Inst *s = static_cast<Inst *>(p);
    while (frames > 0) {
        int n = frames < MAX_FRAMES ? frames : MAX_FRAMES;
        for (int j = 0; j < n; j++) {
            s->in[0][j] = in[2 * j] * (1.0f / 32768.0f);
            s->in[1][j] = in[2 * j + 1] * (1.0f / 32768.0f);
        }
        float *ins[2] = {s->in[0], s->in[1]}, *outs[2] = {s->out[0], s->out[1]};
        s->fx.processReplacing(ins, outs, n);
        for (int j = 0; j < n; j++) {
            out[2 * j] = to_s16(s->out[0][j]);
            out[2 * j + 1] = to_s16(s->out[1][j]);
        }
        in += 2 * n;
        out += 2 * n;
        frames -= n;
    }
}

const mpc_engine_t ENGINE = {create, destroy, midi, set_param, get_param, render, process};

}  // namespace

const mpc_engine_t *mpc_engine(void) { return &ENGINE; }
