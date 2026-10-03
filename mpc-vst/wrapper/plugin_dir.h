/* Where is this plugin? The directory its own .so was loaded from, so an engine can find presets, banks, ROMs and
 * other files shipped next to it wherever it was installed (/sdcard/Synths/<folder>, /media/<card>/Synths/<folder>,
 * or the old /sdcard/vst): no hardcoded /sdcard, and no need to parse MPC.settings. dladdr() reports the path the host passed to dlopen(), which is the
 * file= path from the plugin list.
 *
 *   char dir[512];
 *   if (mpc_plugin_dir(dir, sizeof dir)) ...      dir = "/sdcard/Synths/<folder>", no trailing slash
 *
 * Define _GNU_SOURCE before the first #include (vst2_wrap.c does). Header-only, static inline. Needs dladdr (glibc >= 2.34 has it in libc; older glibc needs -ldl). Returns 1 on
 * success, 0 if it can't tell (buf is then ""). Falls back to /proc/self/maps if dladdr gives no usable path. */
#ifndef MPC_PLUGIN_DIR_H
#define MPC_PLUGIN_DIR_H

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

static inline int mpc_dirname_of(const char *path, char *buf, size_t n) {
    const char *slash = strrchr(path, '/');
    size_t len = slash ? (size_t)(slash - path) : 0;
    if (!slash || len == 0 || len >= n) return 0;
    memcpy(buf, path, len);
    buf[len] = 0;
    return 1;
}

static inline int mpc_plugin_dir(char *buf, size_t n) {
    Dl_info info;
    if (n) buf[0] = 0;
    if (!n) return 0;
    if (dladdr((void *)&mpc_plugin_dir, &info) && info.dli_fname && info.dli_fname[0] == '/' &&
        mpc_dirname_of(info.dli_fname, buf, n))
        return 1;
    FILE *f = fopen("/proc/self/maps", "r");   /* fallback: the mapping that contains this function */
    if (!f) return 0;
    char line[1024];
    unsigned long me = (unsigned long)&mpc_plugin_dir;
    int ok = 0;
    while (!ok && fgets(line, sizeof line, f)) {
        unsigned long lo, hi;
        char *p = strchr(line, '/');
        if (sscanf(line, "%lx-%lx", &lo, &hi) == 2 && me >= lo && me < hi && p) {
            p[strcspn(p, "\n")] = 0;
            ok = mpc_dirname_of(p, buf, n);
        }
    }
    fclose(f);
    return ok;
}

#endif
