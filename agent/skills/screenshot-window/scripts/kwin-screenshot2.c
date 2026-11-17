/*
 * Authorized KWin ScreenShot2 CaptureWindow client.
 *
 * KWin matches /proc/<pid>/exe to a .desktop Exec= and requires
 * X-KDE-DBUS-Restricted-Interfaces=org.kde.KWin.ScreenShot2.
 * A Python interpreter cannot satisfy that, so this small binary is the
 * D-Bus caller. It does not activate the target window and does not notify.
 *
 * SPDX-License-Identifier: MIT
 */

#define _GNU_SOURCE

#include <dbus/dbus.h>
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <limits.h>
#include <png.h>
#include <poll.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define SERVICE "org.kde.KWin.ScreenShot2"
#define OBJECT "/org/kde/KWin/ScreenShot2"
#define IFACE "org.kde.KWin.ScreenShot2"

#define QIMAGE_RGB32 4
#define QIMAGE_ARGB32 5
#define QIMAGE_ARGB32_PREMULT 6
#define QIMAGE_RGBA8888 17
#define QIMAGE_RGBA8888_PREMULT 18

#define MAX_IMAGE_BYTES (256u * 1024u * 1024u)
#define TIMEOUT_MS 30000

struct options {
	const char *handle;
	const char *output;
	dbus_bool_t decoration;
	dbus_bool_t cursor;
	dbus_bool_t shadow;
	dbus_bool_t native;
};

struct reply_meta {
	char type[32];
	uint32_t width;
	uint32_t height;
	uint32_t stride;
	uint32_t format;
	bool ok;
	char err_name[256];
	char err_msg[512];
};

static void die(const char *msg)
{
	fprintf(stderr, "kwin-screenshot2: %s\n", msg);
	exit(1);
}

static void die_errno(const char *msg)
{
	fprintf(stderr, "kwin-screenshot2: %s: %s\n", msg, strerror(errno));
	exit(1);
}

static unsigned unpre(unsigned c, unsigned a)
{
	if (a == 0) {
		return 0;
	}
	if (a == 255) {
		return c;
	}
	unsigned v = (c * 255u + (a / 2u)) / a;
	return v > 255u ? 255u : v;
}

static void append_bool_option(DBusMessageIter *array, const char *key, dbus_bool_t value)
{
	DBusMessageIter dict;
	DBusMessageIter variant;

	dbus_message_iter_open_container(array, DBUS_TYPE_DICT_ENTRY, NULL, &dict);
	dbus_message_iter_append_basic(&dict, DBUS_TYPE_STRING, &key);
	dbus_message_iter_open_container(&dict, DBUS_TYPE_VARIANT, "b", &variant);
	dbus_message_iter_append_basic(&variant, DBUS_TYPE_BOOLEAN, &value);
	dbus_message_iter_close_container(&dict, &variant);
	dbus_message_iter_close_container(array, &dict);
}

static void parse_reply(DBusMessage *reply, struct reply_meta *meta)
{
	memset(meta, 0, sizeof(*meta));
	strcpy(meta->type, "raw");

	if (dbus_message_get_type(reply) == DBUS_MESSAGE_TYPE_ERROR) {
		const char *name = dbus_message_get_error_name(reply);
		const char *msg = NULL;
		DBusError err;
		dbus_error_init(&err);
		dbus_message_get_args(reply, &err, DBUS_TYPE_STRING, &msg, DBUS_TYPE_INVALID);
		snprintf(meta->err_name, sizeof(meta->err_name), "%s", name ? name : "error");
		snprintf(meta->err_msg, sizeof(meta->err_msg), "%s", msg ? msg : (err.message ? err.message : ""));
		dbus_error_free(&err);
		return;
	}

	DBusMessageIter iter;
	if (!dbus_message_iter_init(reply, &iter) || dbus_message_iter_get_arg_type(&iter) != DBUS_TYPE_ARRAY) {
		snprintf(meta->err_name, sizeof(meta->err_name), "bad-reply");
		snprintf(meta->err_msg, sizeof(meta->err_msg), "expected a{sv} results");
		return;
	}

	DBusMessageIter array;
	dbus_message_iter_recurse(&iter, &array);
	while (dbus_message_iter_get_arg_type(&array) == DBUS_TYPE_DICT_ENTRY) {
		DBusMessageIter dict;
		DBusMessageIter variant;
		const char *key = NULL;

		dbus_message_iter_recurse(&array, &dict);
		if (dbus_message_iter_get_arg_type(&dict) != DBUS_TYPE_STRING) {
			dbus_message_iter_next(&array);
			continue;
		}
		dbus_message_iter_get_basic(&dict, &key);
		dbus_message_iter_next(&dict);
		if (dbus_message_iter_get_arg_type(&dict) != DBUS_TYPE_VARIANT) {
			dbus_message_iter_next(&array);
			continue;
		}
		dbus_message_iter_recurse(&dict, &variant);
		int t = dbus_message_iter_get_arg_type(&variant);
		if (key && strcmp(key, "type") == 0 && t == DBUS_TYPE_STRING) {
			const char *v = NULL;
			dbus_message_iter_get_basic(&variant, &v);
			if (v) {
				snprintf(meta->type, sizeof(meta->type), "%s", v);
			}
		} else if (key && t == DBUS_TYPE_UINT32) {
			uint32_t v = 0;
			dbus_message_iter_get_basic(&variant, &v);
			if (strcmp(key, "width") == 0) {
				meta->width = v;
			} else if (strcmp(key, "height") == 0) {
				meta->height = v;
			} else if (strcmp(key, "stride") == 0) {
				meta->stride = v;
			} else if (strcmp(key, "format") == 0) {
				meta->format = v;
			}
		}
		dbus_message_iter_next(&array);
	}

	if (meta->width == 0 || meta->height == 0 || meta->stride == 0) {
		snprintf(meta->err_name, sizeof(meta->err_name), "bad-reply");
		snprintf(meta->err_msg, sizeof(meta->err_msg), "missing width/height/stride");
		return;
	}
	meta->ok = true;
}

static bool row_to_rgba(const uint8_t *src, uint32_t width, uint32_t format, uint8_t *dst)
{
	uint32_t x;
	switch (format) {
	case QIMAGE_RGB32:
	case QIMAGE_ARGB32:
	case QIMAGE_ARGB32_PREMULT:
		for (x = 0; x < width; x++) {
			unsigned b = src[x * 4 + 0];
			unsigned g = src[x * 4 + 1];
			unsigned r = src[x * 4 + 2];
			unsigned a = (format == QIMAGE_RGB32) ? 255u : src[x * 4 + 3];
			if (format == QIMAGE_ARGB32_PREMULT) {
				r = unpre(r, a);
				g = unpre(g, a);
				b = unpre(b, a);
			}
			dst[x * 4 + 0] = (uint8_t)r;
			dst[x * 4 + 1] = (uint8_t)g;
			dst[x * 4 + 2] = (uint8_t)b;
			dst[x * 4 + 3] = (uint8_t)a;
		}
		return true;
	case QIMAGE_RGBA8888:
	case QIMAGE_RGBA8888_PREMULT:
		for (x = 0; x < width; x++) {
			unsigned r = src[x * 4 + 0];
			unsigned g = src[x * 4 + 1];
			unsigned b = src[x * 4 + 2];
			unsigned a = src[x * 4 + 3];
			if (format == QIMAGE_RGBA8888_PREMULT) {
				r = unpre(r, a);
				g = unpre(g, a);
				b = unpre(b, a);
			}
			dst[x * 4 + 0] = (uint8_t)r;
			dst[x * 4 + 1] = (uint8_t)g;
			dst[x * 4 + 2] = (uint8_t)b;
			dst[x * 4 + 3] = (uint8_t)a;
		}
		return true;
	default:
		return false;
	}
}

static int write_png(const char *path, const uint8_t *raw, const struct reply_meta *meta)
{
	if (meta->stride < meta->width * 4u) {
		fprintf(stderr, "kwin-screenshot2: stride %u too small for width %u\n", meta->stride, meta->width);
		return 1;
	}

	FILE *fp = fopen(path, "wb");
	if (!fp) {
		die_errno("fopen output");
	}

	png_structp png = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
	png_infop info = png ? png_create_info_struct(png) : NULL;
	if (!png || !info) {
		fclose(fp);
		die("png_create_write_struct failed");
	}
	if (setjmp(png_jmpbuf(png))) {
		png_destroy_write_struct(&png, &info);
		fclose(fp);
		die("libpng failed");
	}

	png_init_io(png, fp);
	png_set_IHDR(png, info, meta->width, meta->height, 8, PNG_COLOR_TYPE_RGBA, PNG_INTERLACE_NONE,
		     PNG_COMPRESSION_TYPE_DEFAULT, PNG_FILTER_TYPE_DEFAULT);
	png_write_info(png, info);

	uint8_t *row = malloc((size_t)meta->width * 4u);
	if (!row) {
		die("out of memory");
	}
	for (uint32_t y = 0; y < meta->height; y++) {
		const uint8_t *src = raw + ((size_t)y * meta->stride);
		if (!row_to_rgba(src, meta->width, meta->format, row)) {
			free(row);
			png_destroy_write_struct(&png, &info);
			fclose(fp);
			fprintf(stderr, "kwin-screenshot2: unsupported QImage format %u\n", meta->format);
			return 1;
		}
		png_write_row(png, row);
	}
	free(row);
	png_write_end(png, NULL);
	png_destroy_write_struct(&png, &info);
	fclose(fp);
	return 0;
}

static int remaining_timeout(struct timespec start)
{
	struct timespec now;
	clock_gettime(CLOCK_MONOTONIC, &now);
	int elapsed = (int)((now.tv_sec - start.tv_sec) * 1000 + (now.tv_nsec - start.tv_nsec) / 1000000);
	int left = TIMEOUT_MS - elapsed;
	return left < 0 ? 0 : left;
}

static int capture(const struct options *opt)
{
	int fds[2];
	if (pipe2(fds, O_CLOEXEC) != 0) {
		die_errno("pipe2");
	}
	int pipe_rd = fds[0];
	int pipe_wr = fds[1];

	DBusError err;
	dbus_error_init(&err);
	DBusConnection *conn = dbus_bus_get(DBUS_BUS_SESSION, &err);
	if (!conn) {
		fprintf(stderr, "kwin-screenshot2: dbus: %s\n", err.message);
		exit(1);
	}
	dbus_connection_set_exit_on_disconnect(conn, FALSE);

	DBusMessage *msg = dbus_message_new_method_call(SERVICE, OBJECT, IFACE, "CaptureWindow");
	if (!msg) {
		die("dbus_message_new_method_call failed");
	}

	DBusMessageIter args;
	DBusMessageIter array;
	dbus_message_iter_init_append(msg, &args);
	const char *handle = opt->handle;
	if (!dbus_message_iter_append_basic(&args, DBUS_TYPE_STRING, &handle)) {
		die("append handle failed");
	}
	if (!dbus_message_iter_open_container(&args, DBUS_TYPE_ARRAY, "{sv}", &array)) {
		die("open options failed");
	}
	append_bool_option(&array, "include-decoration", opt->decoration);
	append_bool_option(&array, "include-cursor", opt->cursor);
	append_bool_option(&array, "include-shadow", opt->shadow);
	append_bool_option(&array, "native-resolution", opt->native);
	if (!dbus_message_iter_close_container(&args, &array)) {
		die("close options failed");
	}
	if (!dbus_message_iter_append_basic(&args, DBUS_TYPE_UNIX_FD, &pipe_wr)) {
		die("append unix fd failed (session bus must support fd passing)");
	}

	DBusPendingCall *pending = NULL;
	if (!dbus_connection_send_with_reply(conn, msg, &pending, TIMEOUT_MS) || !pending) {
		die("send CaptureWindow failed");
	}
	dbus_message_unref(msg);
	dbus_connection_flush(conn);
	close(pipe_wr);
	pipe_wr = -1;

	int dbus_fd = -1;
	if (!dbus_connection_get_unix_fd(conn, &dbus_fd) || dbus_fd < 0) {
		die("dbus unix fd missing");
	}

	int pflags = fcntl(pipe_rd, F_GETFL, 0);
	if (pflags >= 0) {
		fcntl(pipe_rd, F_SETFL, pflags | O_NONBLOCK);
	}

	uint8_t *buf = NULL;
	size_t buflen = 0;
	size_t bufcap = 0;
	bool eof = false;
	bool got_reply = false;
	DBusMessage *reply = NULL;
	struct timespec start;
	clock_gettime(CLOCK_MONOTONIC, &start);

	while (true) {
		/* Reply may already sit in libdbus's buffer; poll() on the socket
		 * will not wake in that case. Drain every iteration. */
		dbus_connection_read_write(conn, 0);
		while (dbus_connection_dispatch(conn) == DBUS_DISPATCH_DATA_REMAINS) {
		}
		if (!got_reply && dbus_pending_call_get_completed(pending)) {
			reply = dbus_pending_call_steal_reply(pending);
			got_reply = true;
		}

		while (!eof) {
			if (buflen == bufcap) {
				size_t ncap = bufcap ? bufcap * 2 : 1u << 20;
				if (ncap > MAX_IMAGE_BYTES) {
					ncap = MAX_IMAGE_BYTES;
				}
				if (ncap <= bufcap) {
					die("image exceeds 256 MiB cap");
				}
				uint8_t *nbuf = realloc(buf, ncap);
				if (!nbuf) {
					die("out of memory");
				}
				buf = nbuf;
				bufcap = ncap;
			}
			ssize_t r = read(pipe_rd, buf + buflen, bufcap - buflen);
			if (r < 0) {
				if (errno == EINTR) {
					continue;
				}
				if (errno == EAGAIN || errno == EWOULDBLOCK) {
					break;
				}
				die_errno("read pipe");
			}
			if (r == 0) {
				eof = true;
				break;
			}
			buflen += (size_t)r;
		}

		if (got_reply) {
			if (reply && dbus_message_get_type(reply) == DBUS_MESSAGE_TYPE_ERROR) {
				break;
			}
			if (eof) {
				break;
			}
		}

		int timeout = remaining_timeout(start);
		if (timeout == 0) {
			die("timed out waiting for ScreenShot2");
		}
		struct pollfd pfd[2];
		nfds_t n = 0;
		if (!eof) {
			pfd[n].fd = pipe_rd;
			pfd[n].events = POLLIN | POLLHUP;
			n++;
		}
		if (!got_reply) {
			pfd[n].fd = dbus_fd;
			pfd[n].events = POLLIN;
			n++;
		}
		if (n == 0) {
			break;
		}
		int pr = poll(pfd, n, timeout);
		if (pr < 0) {
			if (errno == EINTR) {
				continue;
			}
			die_errno("poll");
		}
		if (pr == 0) {
			die("timed out waiting for ScreenShot2");
		}
	}

	dbus_pending_call_unref(pending);
	close(pipe_rd);

	if (!reply) {
		die("no D-Bus reply");
	}

	struct reply_meta meta;
	parse_reply(reply, &meta);
	dbus_message_unref(reply);

	if (!meta.ok) {
		fprintf(stderr, "kwin-screenshot2: %s: %s\n", meta.err_name, meta.err_msg);
		if (strstr(meta.err_name, "NotAuthorized") || strstr(meta.err_msg, "authorized")) {
			fprintf(stderr,
				"kwin-screenshot2: install a .desktop with Exec= this binary and\n"
				"  X-KDE-DBUS-Restricted-Interfaces=org.kde.KWin.ScreenShot2\n"
				"then run kbuildsycoca6. `screenshot-window doctor` does that.\n");
		}
		free(buf);
		return 1;
	}

	size_t expect = (size_t)meta.stride * (size_t)meta.height;
	if (buflen < expect) {
		fprintf(stderr, "kwin-screenshot2: short image (%zu bytes, expected %zu)\n", buflen, expect);
		free(buf);
		return 1;
	}

	if (write_png(opt->output, buf, &meta) != 0) {
		free(buf);
		return 1;
	}
	free(buf);

	char resolved[PATH_MAX];
	if (realpath(opt->output, resolved)) {
		printf("%s\n", resolved);
	} else {
		printf("%s\n", opt->output);
	}
	return 0;
}

static void usage(FILE *fp)
{
	fprintf(fp,
		"Usage: kwin-screenshot2 --handle UUID --output FILE.png [options]\n"
		"  --handle UUID          KWin internalId, with or without braces\n"
		"  --output FILE          PNG path\n"
		"  --decoration / --no-decoration   (default: decoration)\n"
		"  --cursor / --no-cursor           (default: no cursor)\n"
		"  --shadow / --no-shadow           (default: no shadow)\n"
		"  --native / --no-native           (default: native resolution)\n"
		"Does not activate the window. Does not emit a notification.\n");
}

int main(int argc, char **argv)
{
	struct options opt = {
		.handle = NULL,
		.output = NULL,
		.decoration = TRUE,
		.cursor = FALSE,
		.shadow = FALSE,
		.native = TRUE,
	};

	static const struct option longopts[] = {
		{"handle", required_argument, NULL, 'H'},
		{"output", required_argument, NULL, 'o'},
		{"decoration", no_argument, NULL, 'D'},
		{"no-decoration", no_argument, NULL, 'd'},
		{"cursor", no_argument, NULL, 'C'},
		{"no-cursor", no_argument, NULL, 'c'},
		{"shadow", no_argument, NULL, 'S'},
		{"no-shadow", no_argument, NULL, 's'},
		{"native", no_argument, NULL, 'N'},
		{"no-native", no_argument, NULL, 'n'},
		{"help", no_argument, NULL, 'h'},
		{0, 0, 0, 0},
	};

	int c;
	while ((c = getopt_long(argc, argv, "H:o:h", longopts, NULL)) != -1) {
		switch (c) {
		case 'H':
			opt.handle = optarg;
			break;
		case 'o':
			opt.output = optarg;
			break;
		case 'D':
			opt.decoration = TRUE;
			break;
		case 'd':
			opt.decoration = FALSE;
			break;
		case 'C':
			opt.cursor = TRUE;
			break;
		case 'c':
			opt.cursor = FALSE;
			break;
		case 'S':
			opt.shadow = TRUE;
			break;
		case 's':
			opt.shadow = FALSE;
			break;
		case 'N':
			opt.native = TRUE;
			break;
		case 'n':
			opt.native = FALSE;
			break;
		case 'h':
			usage(stdout);
			return 0;
		default:
			usage(stderr);
			return 2;
		}
	}

	if (!opt.handle || !opt.output) {
		usage(stderr);
		return 2;
	}

	char handle_buf[80];
	if (opt.handle[0] != '{') {
		snprintf(handle_buf, sizeof(handle_buf), "{%s}", opt.handle);
		opt.handle = handle_buf;
	}

	return capture(&opt);
}
