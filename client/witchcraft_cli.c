#include <stdbool.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <pwd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>

#define log_error(msg, ...)                                             \
    fprintf(stderr, "line %d: " msg "\n", __LINE__, ## __VA_ARGS__)

/** Send the command line arguments to the server.

    @param fd The file descriptor to write the data to.
    @param argc The number of entries in `argv`
    @param argv The array of arguments to write to `fd`.
    @return 0 on success, -1 on failure.
 */
int send_args(int fd, int argc, char** argv) {
    uint32_t total_length = 0;
    ssize_t* lengths = calloc(argc, sizeof(ssize_t));
    if (!lengths) {
        log_error("failed to allocate lengths array");
        return -1;
    }

    for (int ix = 0; ix < argc; ++ix) {
        size_t length = strlen(argv[ix]);
        if (length > SSIZE_MAX) {
            log_error("strlen(argv[%d]) > SSIZE_MAX (%ld)", ix, length);
            free(lengths);
            return -1;
        }

        lengths[ix] = length;

        if (__builtin_add_overflow(total_length, lengths[ix], &total_length)) {
            log_error("msg length would overflow a 32 bit unsigned integer");
            free(lengths);
            return -1;
        }
    }

    /* we add a ' ' between each argv entry */
    if (__builtin_add_overflow(total_length,
                               (argc) ? argc - 1 : 0,
                               &total_length)) {
        log_error("msg length would overflow a 32 bit unsigned integer");
        free(lengths);
        return -1;
    }

    if (write(fd, (char*) &total_length, 4) != 4) {
        log_error("failed to write msg length");
        free(lengths);
        return -1;
    }

    for (int ix = 0; ix < argc; ++ix) {
        if (write(fd, argv[ix], lengths[ix]) != lengths[ix]) {
            log_error("failed to write argv[%d]", ix);
            free(lengths);
            return -1;
        }

        if (ix != argc - 1) {
            if (write(fd, " ", 1) != 1) {
                log_error("failed to write ' ' after argv[%d]", ix);
                free(lengths);
                return -1;
            }
        }
    }

    free(lengths);
    return 0;
}

/** Read one string response from the server.

    @param fd The file descriptor to read from.
    @return A pointer to a heap allocated string on success, NULL on failure.
    @note If a non-null value is returned, the caller must call `free` on it.
 */
char* read_response(int fd) {
    uint32_t size;
    if (read(fd, &size, sizeof(size)) != sizeof(size)) {
        log_error("failed to read msg length");
        return NULL;
    }

    /* allocate one extra character to hold a trailing null byte */
    char* out = malloc(size + 1);
    if (!out) {
        log_error("failed to allocate msg buffer");
        return NULL;
    }
    /* ensure a trailing null byte in the received string */
    out[size] = '\0';

    /* read up to `size` bytes from the file descriptor incrementally filling
       the output buffer */
    uint32_t offset = 0;
    while (offset != size) {
        ssize_t bytes;
        if ((bytes = read(fd, &out[offset], size - offset)) < 0) {
            log_error("failed to read msg: %s", strerror(errno));
            free(out);
            return NULL;
        }
        offset += bytes;
    }

    return out;
}

int find_socket_path(char* socket_path, size_t socket_path_length) {
    static const char* const default_music_home = "/var/lib/witchcraft";
    static const char* const sockname = ".cli-server.sock";

    const char* music_home = getenv("WITCHCRAFT_MUSIC_HOME");

    if (!music_home) {
        music_home = default_music_home;
    }

    size_t music_home_size = strlen(music_home);

    /* we need space for the music home, the sockname file name, add 1 for a
       '/' character and 1 for a null terminator */
    size_t total_size = music_home_size + strlen(sockname) + 2;
    if (total_size > socket_path_length) {
        log_error("socket_path length cannot exceed %ld bytes, got: %ld",
                  socket_path_length,
                  total_size);
        return -1;
    }

    memcpy(socket_path, music_home, music_home_size);
    socket_path[music_home_size] = '/';
    strcpy(&socket_path[music_home_size + 1], sockname);

    return 0;
}

/** Push back data into a heap allocated vector.

    @param size The current size of the vector.
    @param capacity The current capacity of the vector.
    @param vec The vector to insert into.
    @param string The element to insert into the vector.
    @return 0 on success, -1 on failure.
 */
int push_back(size_t* size,
              size_t* capacity,
              const char*** vec,
              const char* string) {
    if (*size == *capacity) {
        *capacity *= 2;
        const char** new_vec = realloc(*vec, *capacity * sizeof(char*));
        if (!new_vec) {
            return -1;
        }
        *vec = new_vec;
    }

    (*vec)[*size] = string;
    *size += 1;
    return 0;
}

/** Handle execution of the `play` command.

    @param out The output from the cli server.
    @return -1 on failure.
    @note This function does not return if it succeeds.
 */
int handle_play(char* out) {
    size_t size = 0;
    size_t capacity = 8;
    const char** argv = calloc(capacity, sizeof(char*));
    if (!argv) {
        log_error("failed to allocate argv");
        return -1;
    }

    /* argv[0] should be the program name */
    push_back(&size, &capacity, &argv, "mpv");

    for (char* end = strchr(out, '\n');
         end;
         out = end + 1, end = strchr(out, '\n')) {
        *end = '\0';
        if (push_back(&size, &capacity, &argv, out)) {
            log_error("push_back failed");
            free(argv);
            return -1;
        }
    }

    /* add the --no-video to not display the cover art */
    push_back(&size, &capacity, &argv, "--no-video");

    /* null terminate the argv list */
    push_back(&size, &capacity, &argv, NULL);

    if (execvp("mpv", (char**) argv)) {
      log_error("execv failed: %s", strerror(errno));

      /* on success we are just going to leak argv, whatever */
      free(argv);
      return -1;
    }

    return 0;
}

int main(int argc, char** argv) {
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) {
        log_error("failed to create socket");
        return -1;
    }

    struct sockaddr_un addr = {0};
    addr.sun_family = AF_UNIX;
    if (find_socket_path(addr.sun_path, sizeof(addr.sun_path))) {
        close(fd);
        return -1;
    }

    if (connect(fd, (struct sockaddr*) &addr, sizeof(addr))) {
        log_error("failed to connect: %s", strerror(errno));
        close(fd);
        return -1;
    }

    /* the play command requires us to execvpe `mpv`, we will need to treat
       this differently */
    bool is_play = argc >= 2 && strcmp(argv[1], "play") == 0;

    if (send_args(fd, argc - 1, &argv[1])) {
        close(fd);
        return -1;
    }

    char result;
    if (read(fd, &result, 1) != 1) {
        log_error("failed to read process result");
        close(fd);
        return -1;
    }

    char* out = read_response(fd);
    if (!out) {
        log_error("failed to read stdout");
        close(fd);
        return -1;
    }
    if (!is_play || result) {
        printf(out);
        free(out);
    }

    char* err = read_response(fd);
    if (!err) {
        log_error("failed to read stderr");
        close(fd);
        return -1;
    }
    fprintf(stderr, err);
    free(err);

    close(fd);

    if (is_play && !result) {
        if (handle_play(out)) {
            /* on success we will leak out, whatever */
            free(out);
            return -1;
        }
    }

    return result;
}
