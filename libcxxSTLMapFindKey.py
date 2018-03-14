import os
import sys
import gdb
import itertools

class CxxRbTreeIterator:
    "RbTreeIterator"
    def __init__(self, nodetype, begin, size, fmt):
        self.begin = begin
        self.count = 0
        self.size = size
        self.nodetype = nodetype
        self.fmt = fmt
        if "__iter_pointer" in str(self.nodetype):
            self.nodetype = gdb.lookup_type(str(self.nodetype).replace("__iter_pointer", "__node_pointer"))
            self.begin = self.begin.cast(self.nodetype)

    def __iter__(self):
        return self
    def get_min_node(self, node):
        """
        _NodePtr
        __tree_min(_NodePtr __x) _NOEXCEPT
        {
           while (__x->__left_ != nullptr)
                __x = __x->__left_;
           return __x;
        }
        """
        while node['__left_'] != 0:
            node = node['__left_']
        return node

    def get_next_node(self, node):
        """
        _NodePtr
        __tree_next(_NodePtr __x) _NOEXCEPT
        {
            if (__x->__right_ != nullptr)
                return __tree_min(__x->__right_);
            while (!__tree_is_left_child(__x))
                __x = __x->__parent_;
            return __x->__parent_;
        }
        """
        begin = node.cast(self.nodetype)
        if begin['__right_'] != 0:
            return self.get_min_node(begin['__right_']).cast(self.nodetype)
        while begin != begin['__parent_']['__left_']:
            begin = begin['__parent_'].cast(self.nodetype)
        return begin['__parent_'].cast(self.nodetype)

    def next(self):
        count = self.count
        self.count = self.count + 1
        if count == self.size:
            raise StopIteration
        value_ptr = self.begin.cast(self.nodetype)
        value = value_ptr.dereference()['__value_']
        self.begin = self.get_next_node(self.begin)
        return self.fmt(count, value)

def MapWrapper(type, val):
    dict = {}
    list = []
    begin = val['__tree_']['__begin_node_']
    nodetype = begin.type
    size = val['__tree_']['__pair3_']['__first_']
    fmt = lambda count, value: ('%s' % value['__cc']['first'], '%s' % value['__cc']['second'])
    for k in CxxRbTreeIterator(nodetype, begin, size, fmt):
        list.append(k)
    return list

def decode_BacktraceHeader(val):
    type = gdb.lookup_type("BacktraceHeader").pointer()
    back_header = (gdb.Value(long(val, 16))).cast(type).dereference()
    num_frames = back_header['num_frames']
    frames = back_header['frames']
    i = 0
    while i < num_frames:
        gdb.execute("list * %s" % frames[i])
        i += 1
    print "\n"

class FreeTrackFindMapKey(gdb.Command):
    def __init__(self):
        super(FreeTrackFindMapKey, self).__init__('FreeTrackFindMapKey', gdb.COMMAND_STATUS)

    def invoke(self, arg, from_tty):
        key = 0
        value = 0
        container_name = ""
        argv = gdb.string_to_argv(arg)
        #gWorkingDir = os.path.dirname(args[0])
        if (argv[0] == "--help"):
            print "mtkFindMapKey -c <container name> -k <key>"
            print "example:\n" \
                  "\t\"std::map<int, int> m;\"\n" \
                  "\tmtkFindMapKey -c m -k 0x123"
            return
        elif (argv[0] == "-c"):
            container_name = str(argv[1])
            if (argv[2] == "-k"):
                key = argv[3]
            else:
                print "invlid parameter: '%s'" % argv[2]
                return
        else:
            print "invlid parameter: '%s'" % argv[0]
            return
        container = gdb.parse_and_eval(container_name)
        container_type = container.type
        list = MapWrapper(container_type, container)
        count = 0
        for x in list:
            if x[0] == key:
                count += 1
                print "[%s] = [%s]" % (x[0], x[1])
                decode_BacktraceHeader(x[1])
        if count == 0:
            print "There is no key = %s" % key
        else:
            print "Total %d pairs.\n" % count

FreeTrackFindMapKey()
