// dbloc: move the Deskbar to the top right (BDeskbar API)
#include <Application.h>
#include <Deskbar.h>
#include <stdio.h>
int main()
{
	BApplication app("application/x-vnd.dbloc");
	BDeskbar bar;
	bool expanded = true;
	deskbar_location loc = bar.Location(&expanded);
	printf("was loc=%d expanded=%d\n", (int) loc, (int) expanded);
	status_t err = bar.SetLocation(B_DESKBAR_RIGHT_TOP, expanded);
	printf("SetLocation -> %ld\n", (long) err);
	return 0;
}
