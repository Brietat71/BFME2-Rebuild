// The strategic variant of the shared Apt message-box movie.
// Retail 0x54C770 constructs the common base before installing VA 0x86A6A4.
#pragma once

#include "GameClient/AptMessageBoxMovieClip.h"

class AptStrategicMessageBox : public AptMessageBoxMovieClip
{
public:
	AptStrategicMessageBox();
	virtual ~AptStrategicMessageBox();

	static void CreateSingleton();

private:
	static AptStrategicMessageBox *s_instance;	// 0x00A05FAC (the destructor clears it)
};

typedef char AptStrategicMessageBoxSizeCheck[sizeof(AptStrategicMessageBox) == 0x08 ? 1 : -1];
