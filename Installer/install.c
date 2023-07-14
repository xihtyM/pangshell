#include "install.h"


// _ALLOCATION = any allocation that must be freed inside this file.
// _FREED = any time the allocation is freed.
// they should have an equal count otherwise there is most likely a memory leak.
// the count will always be 1 more than there actually is because of this comment.


int16_t _download(
    const char *url,
    const char *file)
{
    HRESULT hr;

    printf("Installing: %s from %s\n", file, url);

    hr = URLDownloadToFileA(
        NULL,
        url,
        file,
        BINDF_GETNEWESTVERSION,
        NULL);

    // error whilst downloading
    if (hr != S_OK)
    {
        printf(hr == E_OUTOFMEMORY
         ? "Error: Not enough memory to download file.\n"
         : "Error: URL is not valid, please make sure you are using the latest installer.\n");
        return 1;
    }

    return 0;
}


char *split(
    char *str,
    uint32_t index,
    char delim)
{
    char *split;
    int32_t start = 0;
    int32_t length = 0;

    // get the index of the nth newline - or the null
    // terminator if n is larger than the number of newlines
    for (; str[start] && index > 0; start++)
    {
        if (str[start] == delim)
            index--;
    }

    if (!str[start])
        return ""; // End of file, just return empty string.

    // get the length of the line substring and store it in length
    for (; str[start + length] != delim && str[start + length]; length++) {}

    split = malloc(length + 1); // _ALLOCATION

    if (!split)
        return ""; // terminates installation -- TODO: catch

    // copy the substring into split
    for (int32_t index = 0; index < length; index++)
    {
        split[index] = str[index + start];
    }

    // null terminator
    split[length] = 0;

    return split;
}


InstallPath *init_install(
    char *url,
    const char *files)
{
    // url cannot be null
    if (!url)
        return NULL;

    // url with https://raw.githubusercontent.com/ behind it
    char *full_url = malloc(strlen(url) + RAWLEN + 1); // _ALLOCATION

    strcpy(full_url, RAW);
    strcat(full_url, url);

    InstallPath *res = malloc(sizeof(InstallPath)); // _ALLOCATION

    res->url = full_url;

    if (!files)
        res->files = "files";
    else
        res->files = files;

    return res;
}


char *read_files_dat(
    InstallPath *ip)
{
    // url = ip->url + "/" + ip->files
    char *url = malloc(strlen(ip->url) + strlen(ip->files) + 2); // _ALLOCATION

    if (!url)
        return NULL;

    strcpy(url, ip->url);
    strcat(url, "/");
    strcat(url, ip->files);

    // downloads contents of file into ip->files
    // returns null if couldn't download file
    if (_download(url, ip->files))
        return NULL;
    
    free(url); // _FREED BLOCK

    // after downloading, we still need to read the content - open the downloaded file.
    FILE *fp = fopen(ip->files, "r");

    if (!fp)
        return NULL;

    fseek(fp, 0, SEEK_END);
    long filesize = ftell(fp);
    fseek(fp, 0, SEEK_SET);

    char *files = malloc(filesize + 1); // _ALLOCATION

    if (!files)
        return NULL;

    fread(files, filesize, 1, fp);
    fclose(fp);
    remove(ip->files);

    files[filesize] = 0;

    return files;
}


int16_t install_files(
    InstallPath *ip,
    const char *path)
{
    uint32_t lines = 0;
    char *files = read_files_dat(ip); // FREE AFTER LOOP

    if (!files)
        return 1;

    char *filename = " ";

    while (strlen(filename = getline(files, lines++)) > 0)
    {
        int32_t url_length = strlen(ip->url) + strlen(filename) + 1;
        char *url = malloc(url_length + 1); // _ALLOCATION

        if (!url)
            return 1;

        strcpy(url, ip->url);
        strcat(url, "/");
        strcat(url, filename);

        url[url_length] = 0;

        if (path)
        {
            // using realloc is too much a pain and then you would have to shift over
            // the filename to the end - so instead just use normal malloc on a new buffer
            char *full_path = malloc(strlen(filename) + strlen(path) + 2); // _ALLOCATION

            if (!full_path)
                return 1;

            strcpy(full_path, path);
            strcat(full_path, "\\");
            strcat(full_path, filename);

            remove(full_path);

            if (_download(url, full_path))
                return 1;
            free(full_path); // _FREED BLOCK
        }
        else
        {
            remove(filename);

            if (_download(url, filename))
                return 1;
        }

        free(filename); // _FREED BLOCK
        free(url);      // _FREED BLOCK
    }

    free(files); // _FREED BLOCK

    return 0;
}


int mkalldirs(char *path)
{
    uint16_t sub = 0;
    char *dir = malloc(strlen(path) + 1); // _ALLOCATION
    strcpy(dir, split(path, sub++, '\\'));

    if (mkdir(dir) != 0 && errno != EEXIST)
        return -1;

    while (strcmp(path, dir) != 0)
    {
        strcat(dir, "\\"); // add backslash for next path
        strcat(dir, split(path, sub++, '\\'));

        if (mkdir(dir) != 0 && errno != EEXIST)
            return -1;
    }

    free(dir); // _FREED BLOCK
    return 0;
}


int16_t install(
    char *url,
    const char *files,
    char *path)
{
    InstallPath *ip = init_install(url, files);

    if (!ip)
        return 1; // init failed due to memory error (most likely)
    
    // only check if path is not null, the current working
    // directory is guaranteed to exist so no need for check
    if (path) {
        struct stat fileinfo;

        if (stat(path, &fileinfo) < 0 || !S_ISDIR(fileinfo.st_mode))
        {
            // doesn't exist or is not a directory
            // either way we make a new directory
            if (mkalldirs(path) != 0)
                return 2; // failed to create directory
        }
    }

    if (install_files(ip, path))
        return 3; // could not install files into directory
    
    finish_install(ip);

    return 0;
}
