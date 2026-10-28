// AboutDano: show the BeOS R5.1 "Dano" About box (it lives in Dano's libbe.so, picked up from ./lib)
#include <Application.h>
extern void run_be_about();
int main()
{
	BApplication app("application/x-vnd.dano-about");
	run_be_about();
	app.Run();
	return 0;
}
