#include <locale.h>
#include <direct.h>
#include <stdbool.h>

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
    install("xihtyM/PangShell/main", NULL, "Pang\\PangShell");


    _chdir(getenv("WinDir"));
    FILE *bat = fopen("System32\\pangshell.bat", "w");

    if (!bat)
    {
        printf("Error: Couldn't open System32, make sure you are running as administrator.");
        return 1;
    }

    fwrite("@echo off\npy \"%pang%\\PangShell\\pangshell.py\" %*", strlen("@echo off\npy \"%pang%\\PangShell\\pangshell.py\" %*"), 1, bat);
    fclose(bat);

    return 0;
}
