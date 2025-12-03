/*
 * Wine Joystick Test
 * Queries all joysticks via winmm.dll and reports button/axis counts.
 * Compile with: x86_64-w64-mingw32-gcc -o wine_joy_test.exe wine_joy_test.c -lwinmm
 */

#include <windows.h>
#include <mmsystem.h>
#include <stdio.h>

int main() {
    UINT numDevs = joyGetNumDevs();
    printf("NUM_DEVS=%u\n", numDevs);

    UINT found = 0;
    int testFound = 0;
    UINT testButtons = 0;
    UINT testAxes = 0;

    for (UINT i = 0; i < numDevs; i++) {
        JOYCAPSW caps;
        MMRESULT result = joyGetDevCapsW(i, &caps, sizeof(caps));

        if (result == JOYERR_NOERROR) {
            found++;
            printf("JOY_%u_NAME=%ls\n", i, caps.szPname);
            printf("JOY_%u_BUTTONS=%u\n", i, caps.wNumButtons);
            printf("JOY_%u_AXES=%u\n", i, caps.wNumAxes);
            printf("JOY_%u_MAXBUTTONS=%u\n", i, caps.wMaxButtons);
            printf("JOY_%u_MAXAXES=%u\n", i, caps.wMaxAxes);
            printf("JOY_%u_VID=0x%04X\n", i, caps.wMid);
            printf("JOY_%u_PID=0x%04X\n", i, caps.wPid);

            /* Check if this is our test device by name or VID/PID */
            /* Only capture first match with actual buttons */
            if (!testFound || (testButtons == 0 && caps.wNumButtons > 0)) {
                if (wcsstr(caps.szPname, L"Test Gamepad") != NULL ||
                    wcsstr(caps.szPname, L"vJoy") != NULL ||
                    (caps.wMid == 0x1234 && caps.wPid == 0xBEAD)) {
                    testFound = 1;
                    testButtons = caps.wNumButtons;
                    testAxes = caps.wNumAxes;
                }
            }
        }
    }

    printf("FOUND_COUNT=%u\n", found);
    printf("TEST_FOUND=%d\n", testFound);
    printf("TEST_BUTTONS=%u\n", testButtons);
    printf("TEST_AXES=%u\n", testAxes);

    return 0;
}
