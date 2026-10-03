/* The slice of the Steinberg VST2 SDK's AudioEffectX that Airwindows plugin classes touch, so their sources
 * compile unchanged as plain DSP objects. The real VST2 entry point is mpc-vst-plugins' wrapper/vst2_wrap.c;
 * nothing here talks to a host. MPC OS runs at a fixed 44.1 kHz. */
#pragma once
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define __audioeffect__

typedef int32_t VstInt32;
typedef void *audioMasterCallback;

enum VstPlugCategory { kPlugCategUnknown = 0, kPlugCategEffect, kPlugCategSynth };

enum {
    kVstMaxProgNameLen = 24,
    kVstMaxParamStrLen = 8,
    kVstMaxVendorStrLen = 64,
    kVstMaxProductStrLen = 64,
};

static inline char *vst_strncpy(char *dst, const char *src, size_t max) {
    strncpy(dst, src, max);
    dst[max] = 0;
    return dst;
}

static inline void float2string(float value, char *text, size_t max) {
    snprintf(text, max + 1, "%.3f", value);
}

class AudioEffect {
public:
    virtual ~AudioEffect() {}
};

class AudioEffectX : public AudioEffect {
public:
    AudioEffectX(audioMasterCallback, VstInt32, VstInt32) {}
    float getSampleRate() const { return 44100.0f; }
    void setNumInputs(VstInt32) {}
    void setNumOutputs(VstInt32) {}
    void setUniqueID(VstInt32) {}
    void canProcessReplacing(bool = true) {}
    void canDoubleReplacing(bool = true) {}
    void programsAreChunks(bool = true) {}
};
