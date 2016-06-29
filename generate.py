# -- coding: UTF-8 
import os
import clang.cindex
import re


# 需要忽略的关键字
ignores = ['inline', 'virtual']
# 支持重载的运算符
ops = ['+', '-', '*', '/', '==', '<', '<=']

pubs = []


# export format
# ----------------------------------------------------------------------------------------------------
def module_start():
	s = \
	'''
	module(L)
	['''

	return s


def module_end():
	s = '];'

	return s


def def_class(classname):
	s = '	class_<' + classname + '>("' + classname + '")'
	return s


def def_ctor(params):
	s = '	.def(constructor<'
	l = len(params)
	for i in range(l):
		s += params[i]
		if i < l - 1:
			s += ', '

	s += '>())'

	return s		


def def_method(classname, methodname, ret, params):
	s = '		.def("' + methodname + '", '
	s += '(' + ret
	s += '(' + classname + '::*)('
	l = len(params)

	for i in range(l):
		s += params[i]
		if i < l - 1:
			s += ', '
	
	s += '))'
	s += '&' + classname + '::' + methodname + ')'

	return s			


def def_operator(op, params):	
	s = '		.def(self '
	s += op + ' '
	s += 'other<' + params[0] + '>())'

	return s


def def_property(classname, propertyname):
	s = '		.def_readonly("' + propertyname + '", '
	s += '&' + classname + '::' + propertyname + ')'

	return s

def def_enum(name, value):
	s = '		value("' + name + '", ' + str(value) + '), '

	return s



def def_module(content):
	s = module_start()
	s += content
	s += module_end()		

	return s

# ----------------------------------------------------------------------------------------------------



# parse files
# ----------------------------------------------------------------------------------------------------
# 辅助方法，判断当前节点是否处于公有区域
def is_public(node):
	global pubs
	is_public = False
	for a in pubs:
		if a[0] < node.location.line < a[1]:
			is_public = True
			break

	return is_public


def get_params(string):
	params = re.search(r'\((.*)\)', string).group(1)
	return params.split(',')


def parse_public(node, lines):
	global pubs
	pubs = []
	is_public = False
	b = -1
	for c in node.get_children():
		if str(c.kind) == 'CursorKind.CXX_ACCESS_SPEC_DECL':
			if lines[c.location.line-1].find('public') != -1:
				if is_public == False:
					b = c.location.line
				is_public = True
			elif is_public == True:
				pubs.append([b, c.location.line])
				b = -1
				is_public = False

	if b != -1:
		pubs.append([b, 99999])					


def parse_property(classname, node):
	s = ''

	for c in node.get_children():
		if str(c.kind) == 'CursorKind.FIELD_DECL':
			if not is_public(c):
				continue
			s += def_property(classname, c.spelling)

	return s					


def parse_enum(node):
	s = ''

	for c in node.get_children():
		if str(c.kind) == 'CursorKind.ENUM_DECL':
			if not is_public(c):
				continue

			s += '			.enum_("constant")'
			s += '			['
			en = ''
			for cc in c.get_children():
				en += ' ' * 4 + def_enum(cc.spelling, cc.enum_value) + '\n'
			en = en[:-2]
			
			s += en		
						
	return s					


def parse_ctor(classname, node):
	s = ''

	for c in node.get_children():
		if str(c.kind) == 'CursorKind.CONSTRUCTOR':
			if not is_public(c):
				continue
			params = get_params(c.displayname)
			s += def_ctor(params)		

	return s		


# 解析类的成员函数
# className: 类名
# node: 类根节点
# lines: 文件原始内容
def parse_method(classname, node, lines):
	s = ''

	for c in node.get_children():
		if str(c.kind) == 'CursorKind.CXX_METHOD':
			# 非公共区域
			if not is_public(c):
				continue

			# 非运算符重载	
			if str(c.spelling).find('operator') == -1:
				# 查找返回值
				ret = lines[c.location.line-1][:c.location.column-1]
				# 跳过静态函数
				if ret.find('static') != -1:
					continue
				# 清除不需要的关键词	
				for i in ignores:
					ret = ret.replace(i, '')

				ret = re.sub(r'^\s*', '', ret)
				# 分离参数列表
				params = get_params(c.displayname)

				s += def_method(classname, c.spelling, ret, params)

			else: 
				for op in ops:
					if c.spelling.replace('operator', '') == op:
						# 分离参数列表
						params = get_params(c.displayname)
						if len(params) != 1 or params[0] == '':
							break
						s += def_operator(op, params)	
						break	

	return s	
	

# 解析相应名称的类
# node: 文档根节点
# name: 类名
# lines: 文件原始内容
def parse_class(node, name, lines):
	s = ''

	if (str(node.kind) == 'CursorKind.CLASS_DECL' or str(node.kind) == 'CursorKind.STRUCT_DECL') \
		and str(node.spelling) == name and node.is_definition():

		if str(node.kind) == 'CursorKind.CursorKind.STRUCT_DECL':
			global pubs
			pubs.append([0, 99999])
		else:
			parse_public(node, lines)

		s += def_class(name)
		s += parse_ctor(name, node)
		s += parse_method(name, node, lines)
		s += parse_property(name, node)
		s += parse_enum(node)

	for c in node.get_children():
		s += parse_class(c, name, lines)		

	return s	


def parse_cpp(filename, classlist):
	index = clang.cindex.Index.create()
	tu = index.parse(filename, args=['-x', 'c++'])

	f = open(filename)
	lines = f.readlines()
	f.close()

	print '//-------------------------->>' + filename
	s = ''
	s += module_start()

	l = len(classlist)
	for i in range(l):
		s += parse_class(tu.cursor, classlist[i], lines)
		if i < l-1:
			s += ','

	s += module_end()	
	print '//<<--------------------------' + filename 			

	return s


def makedir(filename):
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise      


def export(filename, classlist, exp_dir, exp_fn):
	s = ''
	s = parse_cpp(filename, classlist)

	path = exp_dir + '/' + exp_fn + '_autobind.h'
	makedir(path)

	print '//-------------------------->>' + path

	f = open(path, 'w+')
	f.write(s)
	f.close()

	print '//<<--------------------------' + path	
