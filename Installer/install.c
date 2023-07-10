#include "install.h"

// _ALLOCATION = any allocation that must be freed inside this file.
// _FREED = any time the allocation is freed.
// they should have an equal count otherwise there is most likely a memory leak.
// the count will always be 1 more than there actually is because of this comment.

InstallPath *init_install(
          char *url,
    const char *files)
{
    if (!url)
        return NULL;
    
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

void _download(const char *url, const char *file) {
    HRESULT hr;

    printf("Installing: %s, %s\n", url, file);

    hr = URLDownloadToFileA(
        NULL,
        url,
        file,
        BINDF_GETNEWESTVERSION,
        NULL);


    if (hr != S_OK) {
        printf(hr == E_OUTOFMEMORY ?
              "Error: Not enough memory to download file.\n"
            : "Error: URL is not valid, please make sure you are using the latest installer.\n");
        exit(1);
    }
}

char *read_files_dat(
    InstallPath *ip)
{
    char *url = malloc(strlen(ip->url) + strlen(ip->files) + 2); // _ALLOCATION

    if (!url)
        return NULL;

    strcpy(url, ip->url);
    strcat(url, "/");
    strcat(url, ip->files);

    _download(url, ip->files);
    free(url); // _FREED BLOCK

    FILE *fp = fopen(ip->files, "r");

    if (!fp)
        return NULL;

    fseek(fp, 0, SEEK_END);
    long fsize = ftell(fp);
    fseek(fp, 0, SEEK_SET);

    char *files = malloc(fsize + 1); // _ALLOCATION

    if (!files)
        return NULL;

    fread(files, fsize, 1, fp);
    fclose(fp);
    remove(ip->files);

    files[fsize] = 0;

    return files;
}

char *getline(
    char *str,
    unsigned int line
)
{
    char *split;
    int start;
    int length;

    for (start = 0; str[start] != 0 && line > 0; start++)
    {
        if (str[start] == '\n')
            line--;
    }

    if (str[start] == 0)
        return ""; // Return blank string because there are not enough lines.

    for (length = 0; str[start + length] != '\n' && str[start + length] != 0; length++);

    split = malloc(length + 1); // _ALLOCATION

    if (!split) return ""; // terminates installation -- TODO: catch

    for (int index = 0; index < length; index++)
    {
        split[index] = str[index + start];
    }

    split[length] = 0;

    return split;
}

int install_files(
    InstallPath *ip,
    const char  *path)
{
    unsigned int lines = 0;
    char *files        = read_files_dat(ip); // FREE AFTER LOOP

    if (!files) return 1;

    char *filename     = " ";

    while (strlen(filename = getline(files, lines++)) > 0)
    {
        int url_length = strlen(ip->url) + strlen(filename) + 1;
        char *url = malloc(url_length + 1); // _ALLOCATION

        if (!url) return 1;

        strcpy(url, ip->url);
        strcat(url, "/");
        strcat(url, filename);

        url[url_length] = 0;

        if (path)
        {
            // using realloc is too much a pain and then you would have to shift over
            // the filename to the end - so instead just use normal malloc on a new buffer
            char *full_path = malloc(strlen(filename) + strlen(path) + 2); // _ALLOCATION

            if (!full_path) return 1;

            strcpy(full_path, path);
            strcat(full_path, "\\");
            strcat(full_path, filename);

            _download(url, full_path);
            free(full_path); // _FREED BLOCK
        }
        else 
        {
            _download(url, filename);
        }

        free(filename); // _FREED BLOCK
        free(url); // _FREED BLOCK
    }

    free(files); // _FREED BLOCK

    return 0;
}


void finish_install(
    InstallPath *ip)
{
    free(ip->url); // _FREED BLOCK
    free(ip); // _FREED BLOCK

    ip = NULL;
}
