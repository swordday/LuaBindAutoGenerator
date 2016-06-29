#ifndef CPPS_H
#define CPPS_H

#include <function>

namespace rv
{

class coroutine
{
public:
	coroutine(std::function<void()> fn)
		: fn_(fn)
	{

	}

	coroutine(std::function<void()>&& fn)
		: fn_(fn)
	{

	}

	~coroutine()
	{

	}

	coroutine create(std:function<void()> fn)
	{
		return coroutine(fn);
	}

	bool yield()
	{
		return true;
	}

	bool resume()
	{
		return true;
	}

	template<typename... Args>
	bool resume(Args... args)
	{
		return true;
	}

private:
	std::function<void()> fn_;
};



}


#endif