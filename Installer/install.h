#include <urlmon.h>
#include <stdio.h>
#include <stdlib.h>


#define RAW    "https://raw.githubusercontent.com/"
#define RAWLEN 34


typedef struct InstallPath
{
    char       *url;
    const char *files;
} InstallPath;


/// @brief Initializes the InstallPath struct.
/// @param url in the syntax "github username/repo/branch" (for example "xihtyM/Pang/main").
/// @param files the name of the text file inside the repo containing every file to be downloaded (seperated by newlines).
/// @return Pointer to InstallPath struct - NULL on failure.
InstallPath *init_install(
          char *url,
    const char *files
);


/// @brief Installs all files in ip->url/ip->files file onto computer. (files must be seperated by newline).
/// @param ip pointer to InstallPath struct.
/// @param path the path of installation - NULL indicates the current working directory.
/// @return Nonzero on failure.
/// @warning The path must be a valid path, otherwise the files will not be downloaded.
int install_files(
    InstallPath *ip,
    const char  *path
);


/// @brief Downloads data from a url into the file.
/// @param url url to download data from.
/// @param file path of file to be downloaded (including the filename) - directory must be valid.
void _download(
    const char *url,
    const char *file
);


/// @brief Reads repo/ip->files.
/// @param ip pointer to InstallPath struct.
/// @return Contents of repo/ip->files - NULL on failure
char *read_files_dat(
    InstallPath *ip);


/// @brief Installs files from ip struct into path.
/// @param ip pointer to InstallPath struct.
/// @param path the directory to be installed into.
/// @return Nonzero on failure.
int install_files(
    InstallPath *ip,
    const char  *path);


/// @brief Frees InstallPath struct and sets it to NULL.
/// @param ip pointer to InstallPath struct.
void finish_install(
    InstallPath *ip);
