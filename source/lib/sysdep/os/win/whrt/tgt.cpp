/**
 * =========================================================================
 * File        : tgt.cpp
 * Project     : 0 A.D.
 * Description : Timer implementation using timeGetTime
 * =========================================================================
 */

// license: GPL; see lib/license.txt

// note: WinMM is delay-loaded to avoid dragging it in when this timer
// implementation isn't used. (this is relevant because its startup is
// fairly slow)

#include "precompiled.h"
#include "tgt.h"

#include "counter.h"

#include "lib/sysdep/os/win/win.h"
#include <mmsystem.h>

#if MSC_VERSION
#pragma comment(lib, "winmm.lib")
#endif


// "Guidelines For Providing Multimedia Timer Support" claims that
// speeding the timer up to 2 ms has little impact, while 1 ms
// causes significant slowdown.
static const UINT PERIOD_MS = 2;

class CounterTGT : public ICounter
{
public:
	virtual const char* Name() const
	{
		return "TGT";
	}

	LibError Activate()
	{
		// note: timeGetTime is always available and cannot fail.

		MMRESULT ret = timeBeginPeriod(PERIOD_MS);
		debug_assert(ret == TIMERR_NOERROR);

		return INFO::OK;
	}

	void Shutdown()
	{
		timeEndPeriod(PERIOD_MS);
	}

	bool IsSafe() const
	{
		// the only point of criticism is the possibility of falling behind
		// due to lost interrupts. this can happen to any interrupt-based timer
		// and some systems may lack a counter-based timer, so consider TGT
		// 'safe'. note that it is still only chosen when all other timers fail.
		return true;
	}

	u64 Counter() const
	{
		return timeGetTime();
	}

	size_t CounterBits() const
	{
		return 32;
	}

	double NominalFrequency() const
	{
		return 1000.0;
	}

	double Resolution() const
	{
		return PERIOD_MS*1e-3;
	}
};

ICounter* CreateCounterTGT(void* address, size_t size)
{
	debug_assert(sizeof(CounterTGT) <= size);
	return new(address) CounterTGT();
}
