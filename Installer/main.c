#include <locale.h>
#include <direct.h>
#include <stdbool.h>
#include <sys/stat.h>

#include "install.h"

bool SetPermanentEnvironmentVariable(LPCSTR value, LPCSTR data) {
    HKEY hKey;
    LPCSTR keyPath = "System\\CurrentControlSet\\Control\\Session Manager\\Environment";
    LSTATUS lOpenStatus = RegOpenKeyExA(HKEY_LOCAL_MACHINE, keyPath, 0, KEY_ALL_ACCESS, &hKey);

    if (lOpenStatus == ERROR_SUCCESS) {
        LSTATUS lSetStatus = RegSetValueExA(hKey, value, 0, REG_SZ,(LPBYTE)data, strlen(data) + 1);
        RegCloseKey(hKey);

        if (lSetStatus == ERROR_SUCCESS) {
            SendMessageTimeoutA(HWND_BROADCAST, WM_SETTINGCHANGE, 0, (LPARAM)"Environment", SMTO_BLOCK, 100, NULL);
            return true;
        }
    }

    return false;
}

void pang_mkdir(const char *path) {
    struct stat path_stat;
    stat(path, &path_stat);

    if ((path_stat.st_mode & S_IFMT) != S_IFDIR) {
        if (_mkdir(path) != 0) {
            printf("Error: Failed to create directory. Make sure you are running as an administrator.\nError: %s", strerror(errno));
            exit(1);
        }
    }
}

void set_pang_variable(void)
{
    char *pang_path = malloc(strlen(getenv("AppData")) + strlen("\\Pang") + 1);
    strcpy(pang_path, getenv("AppData"));
    strcat(pang_path, "\\Pang");

    SetPermanentEnvironmentVariable("pang", pang_path);
    free(pang_path);
}

int main(void)
{
    setlocale(LC_ALL, ".utf-8");

    _chdir(getenv("AppData"));
    pang_mkdir("Pang");

    InstallPath *ip = init_install("xihtyM/PangShell/main", NULL);

    if (!ip)
        return 1;

    install_files(ip, "Pang");
    finish_install(ip);

    _chdir(getenv("WinDir"));
    FILE *bat = fopen("System32\\pangshell.bat", "w");

    if (!bat)
    {
        printf("Error: Couldn't open System32, make sure you are running as administrator.");
        return 1;
    }

    fwrite("@echo off\npy \"%pang%\\pangshell.py\" %*", strlen("@echo off\npy \"%pang%\\pangshell.py\" %*"), 1, bat);
    fclose(bat);

    return 0;
}
