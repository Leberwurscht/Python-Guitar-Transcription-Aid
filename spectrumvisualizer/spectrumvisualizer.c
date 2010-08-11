#include <Python.h>
#include "structmember.h"
#include <pygobject.h>

//  http://faq.pygtk.org/index.py?req=show&file=faq23.015.htp

/*static PyObject *create_graph(PyObject *self, PyObject *args)
{
    int graph_size;

    if (!PyArg_ParseTuple(args, "i", &graph_size))
        return NULL;
    boost::adjacency_list <> *testgraph;
    testgraph = new boost::adjacency_list<>(graph_size);
    return Py_BuildValue("i", 10);
}

static PyMethodDef Methods[] = {
    {"create_graph",  create_graph, METH_VARARGS, "Create a graph"},
    {NULL, NULL, 0, NULL}     
};*/

static PyTypeObject *PyGObject_Type=NULL;

typedef struct {
	PyObject_HEAD
//	int size;
//	boost::adjacency_list<> *boostgraph;
	PyGObject *spectrum_element;
} base;

static int base_init(base *self, PyObject *args, PyObject *kwds)
{
//	int graph_size;
	PyGObject *spectrum_element;
	if (!PyArg_ParseTuple(args, "O!", PyGObject_Type, &spectrum_element)) return -1;
	self->spectrum_element = spectrum_element;
	Py_INCREF(spectrum_element);
//	widget = GTK_WIDGET(py_widget->obj);

//	self->size = graph_size;
//	self->boostgraph = new boost::adjacency_list<>(graph_size);
	return 0;
}

static void base_dealloc(base *self)
{
//	delete self->boostgraph;
	Py_XDECREF(self->spectrum_element);
	self->ob_type->tp_free((PyObject*)self);
}

/*static PyObject *graph_dijkstra(graph *self, PyObject *args)
{
	int n1, n2;

	if (!PyArg_ParseTuple(args, "ii", &n1, &n2)) return NULL;

//	boost::vertex_descriptor
	typedef boost::graph_traits < boost::adjacency_list<> >::vertex_descriptor vertex_descriptor;
	std::vector<vertex_descriptor> p( boost::num_vertices(*(self->boostgraph)) );
//	std::vector<int> d( boost::num_vertices(*(self->boostgraph)) );
	vertex_descriptor start = boost::vertex(n1, *(self->boostgraph));
	boost::dijkstra_shortest_paths(*(self->boostgraph), start, boost::predecessor_map(&p[0]));
	return Py_BuildValue("i", 1);
}

static PyObject *graph_add_edge(graph *self, PyObject *args)
{
	int n1, n2;

	if (!PyArg_ParseTuple(args, "ii", &n1, &n2)) return NULL;
	boost::add_edge(n1, n2, *(self->boostgraph));
	return Py_BuildValue("i", 1);
}
*/
static PyMemberDef base_members[] = {
	{"spectrum_element", T_OBJECT, offsetof(base, spectrum_element), 0, "spectrum element"},
//	{"size", T_INT, offsetof(graph, size), 0, "graph size"},
	{NULL}
};

static PyMethodDef base_methods[] = {
/*	{"add_edge", (PyCFunction)graph_add_edge, METH_VARARGS, "add edge"},
	{"add_edge", (PyCFunction)graph_dijkstra, METH_VARARGS, "dijkstra algorithm"},*/
	{NULL}
};

static PyTypeObject baseType = {
	PyObject_HEAD_INIT(NULL)
	0,
	"spectrumvisualizer.base",
	sizeof(base)
};

PyMODINIT_FUNC initspectrumvisualizer(void)
{
	PyObject* mod;
	mod = Py_InitModule3("spectrumvisualizer", NULL, "Spectrum visualizer");

	init_pygobject();
	PyObject *module;
	module = PyImport_ImportModule("gobject");
	PyGObject_Type = (PyTypeObject*)PyObject_GetAttrString(module, "GObject");
	Py_DECREF(module);

	baseType.tp_flags = Py_TPFLAGS_DEFAULT;
	baseType.tp_new = PyType_GenericNew;
	baseType.tp_init = (initproc)base_init;
	baseType.tp_dealloc = (destructor)base_dealloc;
	baseType.tp_members = base_members;
	baseType.tp_methods = base_methods;
	baseType.tp_doc = "spectrum visualizer base object";
	
	PyType_Ready(&baseType);
	Py_INCREF(&baseType);
	PyModule_AddObject(mod, "base", (PyObject*)&baseType);
}
