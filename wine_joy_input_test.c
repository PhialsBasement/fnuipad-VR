/*
 * Wine Joystick Input Test
 * Reads actual joystick axis/button values via winmm.dll
 * Compile with: x86_64-w64-mingw32-gcc -o wine_joy_input_test.exe wine_joy_input_test.c -lwinmm
 *
 * Usage:
 *   wine_joy_input_test.exe [joy_id] [samples]
 *   - joy_id: joystick ID (default 0)
 *   - samples: number of samples to read (default 10)
 */

#include <windows.h>
#include <mmsystem.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    UINT joyId = 0;
    int samples = 10;
    int delay_ms = 50;

    if (argc > 1) joyId = atoi(argv[1]);
    if (argc > 2) samples = atoi(argv[2]);
    if (argc > 3) delay_ms = atoi(argv[3]);

    /* First check if joystick exists */
    JOYCAPSW caps;
    MMRESULT result = joyGetDevCapsW(joyId, &caps, sizeof(caps));
    if (result != JOYERR_NOERROR) {
        printf("ERROR=NO_DEVICE\n");
        printf("JOY_ID=%u\n", joyId);
        return 1;
    }

    printf("JOY_ID=%u\n", joyId);
    printf("JOY_NAME=%ls\n", caps.szPname);
    printf("JOY_VID=0x%04X\n", caps.wMid);
    printf("JOY_PID=0x%04X\n", caps.wPid);
    printf("JOY_AXES=%u\n", caps.wNumAxes);
    printf("JOY_BUTTONS=%u\n", caps.wNumButtons);
    printf("SAMPLES=%d\n", samples);
    printf("DELAY_MS=%d\n", delay_ms);

    /* Track min/max for each axis */
    DWORD xMin = 0xFFFFFFFF, xMax = 0;
    DWORD yMin = 0xFFFFFFFF, yMax = 0;
    DWORD zMin = 0xFFFFFFFF, zMax = 0;
    DWORD rMin = 0xFFFFFFFF, rMax = 0;
    DWORD uMin = 0xFFFFFFFF, uMax = 0;
    DWORD vMin = 0xFFFFFFFF, vMax = 0;
    DWORD buttonsEverPressed = 0;
    int readErrors = 0;
    int readSuccess = 0;

    /* Read samples */
    for (int i = 0; i < samples; i++) {
        JOYINFOEX info;
        info.dwSize = sizeof(info);
        info.dwFlags = JOY_RETURNALL;

        result = joyGetPosEx(joyId, &info);
        if (result == JOYERR_NOERROR) {
            readSuccess++;

            /* Track axis ranges */
            if (info.dwXpos < xMin) xMin = info.dwXpos;
            if (info.dwXpos > xMax) xMax = info.dwXpos;
            if (info.dwYpos < yMin) yMin = info.dwYpos;
            if (info.dwYpos > yMax) yMax = info.dwYpos;
            if (info.dwZpos < zMin) zMin = info.dwZpos;
            if (info.dwZpos > zMax) zMax = info.dwZpos;
            if (info.dwRpos < rMin) rMin = info.dwRpos;
            if (info.dwRpos > rMax) rMax = info.dwRpos;
            if (info.dwUpos < uMin) uMin = info.dwUpos;
            if (info.dwUpos > uMax) uMax = info.dwUpos;
            if (info.dwVpos < vMin) vMin = info.dwVpos;
            if (info.dwVpos > vMax) vMax = info.dwVpos;

            /* Track buttons */
            buttonsEverPressed |= info.dwButtons;

            /* Print sample if verbose (first and last) */
            if (i == 0 || i == samples - 1) {
                printf("SAMPLE_%d_X=%lu\n", i, info.dwXpos);
                printf("SAMPLE_%d_Y=%lu\n", i, info.dwYpos);
                printf("SAMPLE_%d_Z=%lu\n", i, info.dwZpos);
                printf("SAMPLE_%d_R=%lu\n", i, info.dwRpos);
                printf("SAMPLE_%d_BUTTONS=0x%08lX\n", i, info.dwButtons);
            }
        } else {
            readErrors++;
        }

        Sleep(delay_ms);
    }

    printf("READ_SUCCESS=%d\n", readSuccess);
    printf("READ_ERRORS=%d\n", readErrors);

    /* Report axis ranges seen */
    if (readSuccess > 0) {
        printf("X_MIN=%lu\n", xMin);
        printf("X_MAX=%lu\n", xMax);
        printf("X_RANGE=%lu\n", xMax - xMin);
        printf("Y_MIN=%lu\n", yMin);
        printf("Y_MAX=%lu\n", yMax);
        printf("Y_RANGE=%lu\n", yMax - yMin);
        printf("Z_MIN=%lu\n", zMin);
        printf("Z_MAX=%lu\n", zMax);
        printf("Z_RANGE=%lu\n", zMax - zMin);
        printf("R_MIN=%lu\n", rMin);
        printf("R_MAX=%lu\n", rMax);
        printf("R_RANGE=%lu\n", rMax - rMin);
        printf("BUTTONS_PRESSED=0x%08lX\n", buttonsEverPressed);

        /* Count bits set in buttons */
        DWORD b = buttonsEverPressed;
        int buttonCount = 0;
        while (b) {
            buttonCount += b & 1;
            b >>= 1;
        }
        printf("BUTTON_COUNT=%d\n", buttonCount);
    }

    return readErrors > 0 ? 1 : 0;
}
