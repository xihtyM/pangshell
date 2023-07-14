#pragma once

#include <urlmon.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/stat.h>


// define S_ISREG and S_ISDIR for compatibility
#if !defined(S_ISREG) && defined(S_IFMT) && defined(S_IFREG)
#define S_ISREG(m) (((m) & S_IFMT) == S_IFREG)
#endif
#if !defined(S_ISDIR) && defined(S_IFMT) && defined(S_IFDIR)
#define S_ISDIR(m) (((m) & S_IFMT) == S_IFDIR)
#endif


#define RAW "https://raw.githubusercontent.com/"
#define RAWLEN 34


/// @brief Downloads data from a url into the file.
/// @param url url to download data from.
/// @param file path of file to be downloaded (including the filename) - directory must be valid.
/// @return Nonzero on failure.
int16_t _download(
    const char *url,
    const char *file);


/// @brief Gets the substring at the given index.
/// @param str the string that is split.
/// @param index the nth index.
/// @param delim the delimiter.
/// @return The substring of the nth substring delimited by delim. Empty string on failure or end of file.
char *split(
    char *str,
    uint32_t index,
    char delim);


typedef struct InstallPath
{
    char *url;
    const char *files;
} InstallPath;


/// @brief Initializes the InstallPath struct.
/// @param url in the syntax "github username/repo/branch" (for example "xihtyM/Pang/main").
/// @param files the name of the text file inside the repo containing every file to be downloaded (seperated by newlines).
/// @return Pointer to InstallPath struct - NULL on failure.
InstallPath *init_install(
    char *url,
    const char *files);


/// @brief Reads repo/ip->files.
/// @param ip pointer to InstallPath struct.
/// @return Contents of repo/ip->files - NULL on failure
char *read_files_dat(
    InstallPath *ip);


/// @brief Installs all files in ip->url/ip->files file onto computer. (files must be seperated by newline).
/// @param ip pointer to InstallPath struct.
/// @param path the path of installation - NULL indicates the current working directory.
/// @return Nonzero on failure.
/// @warning The path must be a valid path, otherwise the files will not be downloaded.
int16_t install_files(
    InstallPath *ip,
    const char *path);


/// @brief Gets the line at the given index.
/// @param str the string that is split.
/// @param line the line number.
/// @return The substring of the nth line. Empty string on failure or end of file.
inline char *getline(
    char *str,
    uint32_t line)
{
    return split(str, line, '\n');
}


/// @brief Frees InstallPath struct and sets it to NULL.
/// @param ip pointer to InstallPath struct.
inline void finish_install(
    InstallPath *ip)
{
    free(ip->url); // _FREED BLOCK
    free(ip);      // _FREED BLOCK
}


/// @brief Higher level function for general installation of files from github repository.
/// @param url in the syntax "github username/repo/branch" (for example "xihtyM/Pang/main").
/// @param files the name of the text file inside the repo containing every file to be downloaded (seperated by newlines).
/// @param path the directory to install into (if the directory is invalid, a new directory will be created).
/// @return Nonzero on failure.
int16_t install(
    char *url,
    const char *files,
    char *path);
