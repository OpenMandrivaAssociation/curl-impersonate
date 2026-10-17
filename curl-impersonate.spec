%global debug_package %{nil}

Name:		curl-impersonate
Version:	2.2.2
Release:	1
Summary:	curl build that impersonates browser TLS and HTTP handshakes
License:	MIT AND curl AND Apache-2.0 AND BSD-3-Clause AND Zlib
Group:		Networking/Other
URL:		https://github.com/lexiforest/curl-impersonate
Source0:	https://github.com/lexiforest/curl-impersonate/archive/refs/tags/v%{version}.tar.gz
Source1:	https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz
Source2:	https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz
Source3:	https://github.com/google/brotli/archive/refs/tags/v1.2.0.tar.gz
Source4:	https://github.com/google/boringssl/archive/156c7b75ae9b8c3b3f847acf264f17594c3859fb.zip
Source5:	https://github.com/nghttp2/nghttp2/releases/download/v1.63.0/nghttp2-1.63.0.tar.bz2
Source6:	https://github.com/ngtcp2/ngtcp2/releases/download/v1.20.0/ngtcp2-1.20.0.tar.bz2
Source7:	https://github.com/ngtcp2/nghttp3/releases/download/v1.15.0/nghttp3-1.15.0.tar.bz2
Source8:	https://github.com/curl/curl/archive/curl-8_21_0.tar.gz

BuildRequires:	clang
BuildRequires:	cmake
BuildRequires:	ninja
BuildRequires:	patch
BuildRequires:	%mklibname stdc++ -d

Requires:	ca-certificates

%description
curl-impersonate is curl 8.21.0 linked against BoringSSL (Chrome 150) so it
can reproduce browser TLS fingerprints. nghttp2 is pinned at 1.63.0 because
1.65 removed the HTTP/2 priority flag this build still sends. Those libraries,
plus ngtcp2, nghttp3, brotli, zlib, and zstd, are built as private static
archives and merged into one libcurl-impersonate.a. They are not installed as
system libraries.

libidn2 is not built in, so the license stays clear of the bundled
libunistring.

Headers go to %{_libdir}/curl-impersonate/include, not %{_includedir}/curl.
python-curl_cffi links the merged archive from that directory.

%prep
%setup -q
set -euo pipefail
mkdir -p vendor
cp -a %{SOURCE1} vendor/zlib-1.3.1.tar.gz
cp -a %{SOURCE2} vendor/zstd-1.5.7.tar.gz
cp -a %{SOURCE3} vendor/v1.2.0.tar.gz
cp -a %{SOURCE4} vendor/156c7b75ae9b8c3b3f847acf264f17594c3859fb.zip
cp -a %{SOURCE5} vendor/nghttp2-1.63.0.tar.bz2
cp -a %{SOURCE6} vendor/ngtcp2-1.20.0.tar.bz2
cp -a %{SOURCE7} vendor/nghttp3-1.15.0.tar.bz2
cp -a %{SOURCE8} vendor/curl-8_21_0.tar.gz

# The superbuild fetches these by URL. Builds have no network, and the
# upstream release tarball is a prebuilt blob we do not ship.
sed -i \
	-e 's|set(ZLIB_URL "https://github.com/madler/zlib/releases/download/v${ZLIB_VERSION}/zlib-${ZLIB_VERSION}.tar.gz")|set(ZLIB_URL "${CMAKE_CURRENT_SOURCE_DIR}/vendor/zlib-1.3.1.tar.gz")|' \
	-e 's|set(ZSTD_URL "https://github.com/facebook/zstd/releases/download/v${ZSTD_VERSION}/zstd-${ZSTD_VERSION}.tar.gz")|set(ZSTD_URL "${CMAKE_CURRENT_SOURCE_DIR}/vendor/zstd-1.5.7.tar.gz")|' \
	-e 's|set(BROTLI_URL "https://github.com/google/brotli/archive/refs/tags/v${BROTLI_VERSION}.tar.gz")|set(BROTLI_URL "${CMAKE_CURRENT_SOURCE_DIR}/vendor/v1.2.0.tar.gz")|' \
	-e 's|set(BORINGSSL_URL "https://github.com/google/boringssl/archive/${BORINGSSL_COMMIT}.zip")|set(BORINGSSL_URL "${CMAKE_CURRENT_SOURCE_DIR}/vendor/156c7b75ae9b8c3b3f847acf264f17594c3859fb.zip")|' \
	-e 's|set(NGHTTP2_URL "https://github.com/nghttp2/nghttp2/releases/download/v${NGHTTP2_VERSION}/nghttp2-${NGHTTP2_VERSION}.tar.bz2")|set(NGHTTP2_URL "${CMAKE_CURRENT_SOURCE_DIR}/vendor/nghttp2-1.63.0.tar.bz2")|' \
	-e 's|set(NGTCP2_URL "https://github.com/ngtcp2/ngtcp2/releases/download/v${NGTCP2_VERSION}/ngtcp2-${NGTCP2_VERSION}.tar.bz2")|set(NGTCP2_URL "${CMAKE_CURRENT_SOURCE_DIR}/vendor/ngtcp2-1.20.0.tar.bz2")|' \
	-e 's|set(NGHTTP3_URL "https://github.com/ngtcp2/nghttp3/releases/download/v${NGHTTP3_VERSION}/nghttp3-${NGHTTP3_VERSION}.tar.bz2")|set(NGHTTP3_URL "${CMAKE_CURRENT_SOURCE_DIR}/vendor/nghttp3-1.15.0.tar.bz2")|' \
	-e 's|set(CURL_URL "https://github.com/curl/curl/archive/${CURL_VERSION}.tar.gz")|set(CURL_URL "${CMAKE_CURRENT_SOURCE_DIR}/vendor/curl-8_21_0.tar.gz")|' \
	CMakeLists.txt
if grep -E 'set\([A-Z0-9_]*URL "https://' CMakeLists.txt; then
	echo "curl-impersonate still has a network URL" >&2
	exit 1
fi

# Clang 23 drops the whole target attribute when it sees unknown evex512,
# then errors because the AVX-512 body is compiled without avx512f.
grep -q '__clang_major__ >= 18))' patches/curl.patch
sed -i 's/__clang_major__ >= 18))/__clang_major__ >= 18 \&\& __clang_major__ < 23))/' patches/curl.patch
grep -q '__clang_major__ < 23' patches/curl.patch

%build
set -euo pipefail
# Cap each ExternalProject. The superbuild runs several of them at once.
cmake -S . -B build -G Ninja \
	-DCMAKE_BUILD_TYPE=Release \
	-DCMAKE_C_COMPILER=clang \
	-DCMAKE_CXX_COMPILER=clang++ \
	-DCMAKE_INSTALL_PREFIX=%{_prefix} \
	-DUSE_LIBIDN2=OFF \
	-DSUBJOBS=4 \
	-DCURL_CA_BUNDLE=%{_sysconfdir}/pki/tls/certs/ca-bundle.crt
cmake --build build %{?_smp_mflags}

ver=$(build/deps/build/curl/src/curl-impersonate -V)
echo "$ver"
echo "$ver" | grep -q 'BoringSSL'
echo "$ver" | grep -q 'nghttp2/1.63.0'
echo "$ver" | grep -q 'ngtcp2/1.20.0'
echo "$ver" | grep -q 'nghttp3/1.15.0'
if echo "$ver" | grep -E -q 'libidn2|AppleIDN'; then
	echo "IDN support leaked into the build" >&2
	exit 1
fi

deps=build/deps/install/lib
merge=build/merged
rm -rf "$merge"
mkdir -p "$merge"
cp -a build/deps/build/curl/lib/libcurl-impersonate.a "$merge/libcurl-impersonate.orig.a"
cp -a "$deps"/libz.a "$deps"/libzstd.a \
	"$deps"/libbrotlidec.a "$deps"/libbrotlicommon.a "$deps"/libbrotlienc.a \
	"$deps"/libnghttp2.a "$deps"/libnghttp3.a \
	"$deps"/libngtcp2.a "$deps"/libngtcp2_crypto_boringssl.a \
	"$deps"/libssl.a "$deps"/libcrypto.a \
	"$merge/"
(
	cd "$merge"
	clang -r -o libcurl-impersonate.full.o -Wl,--whole-archive \
		libcurl-impersonate.orig.a libz.a libzstd.a \
		libbrotlidec.a libbrotlicommon.a libbrotlienc.a \
		libnghttp2.a libnghttp3.a libngtcp2.a libngtcp2_crypto_boringssl.a \
		libssl.a libcrypto.a \
		-Wl,--no-whole-archive
	rm -f libcurl-impersonate.a
	ar rcs libcurl-impersonate.a libcurl-impersonate.full.o
)

# An empty main() is not enough: --gc-sections drops brotli and BoringSSL
# unless a curl symbol is referenced. BoringSSL is built against libstdc++.
cat > "$merge/linktest.c" <<'EOF'
#include <curl/curl.h>
#include <stdio.h>
int main(void) {
	curl_version_info_data *d = curl_version_info(CURLVERSION_NOW);
	puts(d->version);
	puts(d->ssl_version);
	return 0;
}
EOF
clang -o "$merge/linktest" "$merge/linktest.c" \
	-I build/deps/src/curl/include \
	-Wl,--whole-archive "$merge/libcurl-impersonate.a" -Wl,--no-whole-archive \
	-lstdc++ -lm -pthread -ldl
"$merge/linktest" | grep -q '8.21.0-IMPERSONATE'
"$merge/linktest" | grep -q 'BoringSSL'

mkdir -p packaged-licenses
cp -a LICENSE packaged-licenses/LICENSE-curl-impersonate
cp -a build/deps/src/boringssl/LICENSE packaged-licenses/LICENSE-boringssl
cp -a build/deps/src/brotli/LICENSE packaged-licenses/LICENSE-brotli
cp -a build/deps/src/curl/COPYING packaged-licenses/LICENSE-curl
cp -a build/deps/src/nghttp2/COPYING packaged-licenses/LICENSE-nghttp2
cp -a build/deps/src/nghttp3/COPYING packaged-licenses/LICENSE-nghttp3
cp -a build/deps/src/ngtcp2/COPYING packaged-licenses/LICENSE-ngtcp2
cp -a build/deps/src/zlib/LICENSE packaged-licenses/LICENSE-zlib
cp -a build/deps/src/zstd/LICENSE packaged-licenses/LICENSE-zstd

%install
set -euo pipefail
inst=%{buildroot}%{_libdir}/curl-impersonate
mkdir -p %{buildroot}%{_bindir} %{buildroot}%{_libdir} "$inst/include"
install -m 755 build/deps/build/curl/src/curl-impersonate %{buildroot}%{_bindir}/curl-impersonate
install -m 755 bin/curl_* %{buildroot}%{_bindir}/
cp -a build/deps/build/curl/lib/libcurl-impersonate.so %{buildroot}%{_libdir}/
cp -a build/deps/build/curl/lib/libcurl-impersonate.so.* %{buildroot}%{_libdir}/
cp -a build/deps/src/curl/include/curl "$inst/include/"
rm -f "$inst/include/curl/Makefile.am"
install -m 644 build/merged/libcurl-impersonate.a "$inst/libcurl-impersonate.a"

%files
%doc README.md
%license packaged-licenses/LICENSE-curl-impersonate
%license packaged-licenses/LICENSE-boringssl
%license packaged-licenses/LICENSE-brotli
%license packaged-licenses/LICENSE-curl
%license packaged-licenses/LICENSE-nghttp2
%license packaged-licenses/LICENSE-nghttp3
%license packaged-licenses/LICENSE-ngtcp2
%license packaged-licenses/LICENSE-zlib
%license packaged-licenses/LICENSE-zstd
%{_bindir}/curl-impersonate
%{_bindir}/curl_*
%{_libdir}/libcurl-impersonate.so
%{_libdir}/libcurl-impersonate.so.*
%{_libdir}/curl-impersonate
