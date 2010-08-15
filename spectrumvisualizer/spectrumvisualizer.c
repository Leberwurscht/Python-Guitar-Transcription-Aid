#include <Python.h>
#include "structmember.h"
#include <pygobject.h>
#include <gst/gst.h>

// http://faq.pygtk.org/index.py?req=show&file=faq23.015.htp
// http://cgit.freedesktop.org/gstreamer/gst-plugins-good/tree/tests/examples/spectrum/demo-osssrc.c

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
//PyObject *test;

typedef struct {
	PyGObject gobj;
//	PyObject_HEAD
//	int size;
//	boost::adjacency_list<> *boostgraph;
	PyGObject *spectrum_element;
	PyGObject *bus;
	PyObject *called;
} base;

static gboolean magnitudes_available_signal(GstClock * sync_clock, GstClockTime time, GstClockID id, gpointer user_data)
{
/*	if (GST_CLOCK_TIME_IS_VALID (time))
		g_idle_add (delayed_idle_spectrum_update, user_data);
	else
		g_free (user_data);*/

	return TRUE;
}

static gboolean on_message(GstBus *bus, GstMessage *message, gpointer data)
{
	base *b = data;
	GstElement *spectrum = GST_ELEMENT(b->spectrum_element->obj);
	GstElement *message_element = GST_ELEMENT(GST_MESSAGE_SRC(message));

	if (message_element == spectrum)
	{
		GstClockTime waittime = GST_CLOCK_TIME_NONE;
		const GstStructure *s = gst_message_get_structure(message);

		// determine waittime
		GstClockTime timestamp, duration;

		if (gst_structure_get_clock_time(s, "running-time", &timestamp) && gst_structure_get_clock_time(s, "duration", &duration))
		{
			/* wait for middle of buffer */
			waittime = timestamp + duration/2;
		}
		else if (gst_structure_get_clock_time(s, "endtime", &timestamp))
		{
			waittime = timestamp;
		}

		// delay message
		if (GST_CLOCK_TIME_IS_VALID (waittime))
		{
			GstClockTime basetime = gst_element_get_base_time(spectrum);
		}

//		b->called = Py_BuildValue("i", 1);
//		g_signal_emit_by_name(G_OBJECT((b->gobj).obj), "notify");
		g_signal_emit_by_name(G_OBJECT((b->gobj).obj), "magnitudes_available");
	}
	return TRUE;
}

/*static gboolean on_notify(GObject *obj, GParamSpec *spec, gpointer data)
{
	base *b = data;
	b->called = Py_BuildValue("i", 1);

	return TRUE;
}*/

static int base_init(base *self, PyObject *args, PyObject *kwds)
{
	int l=PyTuple_Size(args);
	PyObject *reduced_args = PySequence_GetSlice(args, 2,l);

	if (PyGObject_Type->tp_init((PyObject *)self, reduced_args, kwds) < 0) return -1;

//	int graph_size;
	PyGObject *spectrum_element;
	PyGObject *bus;
	if (!PyArg_ParseTuple(args, "O!O!", PyGObject_Type, &spectrum_element, PyGObject_Type, &bus)) return -1;
	self->spectrum_element = spectrum_element;
	Py_INCREF(spectrum_element);
	self->bus = bus;
	Py_INCREF(bus);

	self->called = Py_BuildValue("i", 0);

	GstBus *gstbus = GST_BUS(bus->obj);
	gst_bus_add_signal_watch(gstbus);
	g_signal_connect(G_OBJECT(gstbus), "message::element", G_CALLBACK(on_message), self);

//	GstElement *gstelement = GST_ELEMENT(spectrum_element->obj);
////	GstPad *sink = gst_element_get_static_pad(gstelement, "sink");
//	GstPad *sink = gst_element_get_pad(gstelement, "sink");
	
//	int i=g_signal_connect(G_OBJECT(sink), "notify", G_CALLBACK(on_notify), self);
//	self->called = Py_BuildValue("i", i);
//	widget = GTK_WIDGET(py_widget->obj);

//	self->size = graph_size;
//	self->boostgraph = new boost::adjacency_list<>(graph_size);
	return 0;
}

static void base_dealloc(base *self)
{
//	delete self->boostgraph;
	Py_XDECREF(self->spectrum_element);
	Py_XDECREF(self->bus);
//	self->ob_type->tp_free((PyObject*)self);
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
	{"bus", T_OBJECT, offsetof(base, bus), 0, "bus"},
	{"called", T_OBJECT, offsetof(base, called), 0, "called"},
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

	baseType.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE; // second one to allow subclassing (http://groups.google.com/group/comp.lang.python/browse_thread/thread/634752a588a033d6)
	baseType.tp_base = PyGObject_Type;	// inherit from GObject
//	baseType.tp_new = PyType_GenericNew;
	baseType.tp_init = (initproc)base_init;
//	baseType.tp_dealloc = (destructor)base_dealloc;
	baseType.tp_members = base_members;
	baseType.tp_methods = base_methods;
	baseType.tp_doc = "spectrum visualizer base object";
	


	PyType_Ready(&baseType);
//	test = PyObject_GetAttrString((PyObject*)PyGObject_Type, "__gsignals__");
/*	PyObject *d = PyDict_New();
	PyObject *t = PyTuple_Pack(3,
		PyObject_GetAttrString(module, "SIGNAL_RUN_FIRST"),
		PyObject_GetAttrString(module, "TYPE_NONE"),
		PyTuple_Pack(1, PyObject_GetAttrString(module, "TYPE_INT"))
	);
//	PyObject *t = PyTuple_Pack(1, PyObject_GetAttrString((PyObject*)PyGObject_Type, "SIGNAL_RUN_FIRST"));

//	PyObject *t = (PyTypeObject*)PyObject_GetAttrString(module, "SIGNAL_RUN_FIRST");
//	PyObject *t = Py_BuildValue("i", 12);
	PyDict_SetItemString(d, "magnitudes_available", t);*/
/*	Py_INCREF(d);
	Py_INCREF(t);
	PyObject_SetAttrString((PyObject*)&baseType, "__gsignalss__", d);*/
//	PyDict_SetItemString(baseType.tp_dict, "__gsignals__", d);
	Py_INCREF(&baseType);
	PyModule_AddObject(mod, "base", (PyObject*)&baseType);
}
