/*
 * ABI 标识库：让安装包的 native-code 归属真实可查，而不是只写在文档里。
 *
 * 该库只有一处职责：在 arm64-v8a 设备上被加载时回报自身 ABI，
 * 供 health 的 native_abi 字段与排查使用；不承担业务逻辑。
 * 若在非 arm64 设备上加载失败，Java 侧会降级为 "none"，不影响纯 Java 功能。
 */
#include <jni.h>

JNIEXPORT jstring JNICALL
Java_com_letsgolook_aggregator_LglBridge_nativeAbi(JNIEnv *env, jclass clazz) {
    (void) clazz;
    return (*env)->NewStringUTF(env, "arm64-v8a");
}
