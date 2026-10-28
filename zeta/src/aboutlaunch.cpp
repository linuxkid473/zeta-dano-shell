// About launcher: stands in for ZETA's About app and starts the Dano About box (own folder, own libbe.so)
#include <Application.h>
#include <OS.h>
#include <image.h>
extern char **environ;
int main()
{
	BApplication app("application/x-vnd.yT-About");
	const char *argv[2] = { "/boot/home/DanoShell/about/AboutDano", NULL };
	thread_id t = load_image(1, argv, (const char **) environ);
	if (t >= 0)
		resume_thread(t);
	return 0;
}
