#include <Python.h>
#include "structmember.h"
#include <pygobject.h>
#include <gst/gst.h>

// http://faq.pygtk.org/index.py?req=show&file=faq23.015.htp
// http://cgit.freedesktop.org/gstreamer/gst-plugins-good/tree/tests/examples/spectrum/demo-osssrc.c

// for subclassing, will be set by initSpectrumData
static PyTypeObject *PyGObject_Type=NULL;

// "base" class
typedef struct {
	PyGObject gobj;
	PyGObject *spectrum_element;
	PyGObject *pipeline;
	GstClock *sync_clock;
} base;

static PyTypeObject baseType = {
	PyObject_HEAD_INIT(NULL)
	0,
	"SpectrumData.base",
	sizeof(base)
};

static PyMemberDef base_members[] = {
	{"spectrum_element", T_OBJECT, offsetof(base, spectrum_element), 0, "spectrum element"},
	{"pipeline", T_OBJECT, offsetof(base, pipeline), 0, "pipeline"},
	{NULL}
};

// struct for delaying messages
typedef struct {
	GObject *gobj; // gobject on which to emit the signal
	guint bands;
	gint rate;
	gint threshold;
	PyObject *magnitudes;
} spectrum_message;

// fire signals for delayed spectrum messages
static gboolean delayed_spectrum_update(GstClock *sync_clock, GstClockTime time, GstClockID id, gpointer user_data)
{
	spectrum_message *mess = user_data;

	if (GST_CLOCK_TIME_IS_VALID(time))
	{
		g_signal_emit_by_name(mess->gobj, "magnitudes_available", mess->bands, mess->rate, mess->threshold, mess->magnitudes);
	}

	g_object_unref(mess->gobj);
	g_free(mess);

	return TRUE;
}

// get spectrum messages and delay them
static gboolean on_message(GstBus *bus, GstMessage *message, gpointer data)
{
	base *base_object = data;
	GstElement *spectrum = GST_ELEMENT(base_object->spectrum_element->obj);
	gst_object_ref(spectrum);

	GstElement *message_element = GST_ELEMENT(GST_MESSAGE_SRC(message));
	gst_object_ref(message_element);

	if (message_element == spectrum)
	{
		GstClockTime waittime = GST_CLOCK_TIME_NONE;
		const GstStructure *message_structure = gst_message_get_structure(message);

		// determine waittime
		GstClockTime timestamp, duration;

		if (
			   gst_structure_get_clock_time(message_structure, "running-time", &timestamp)
			&& gst_structure_get_clock_time(message_structure, "duration", &duration)
		)
		{
			/* wait for middle of buffer */
			waittime = timestamp + duration/2;
		}
		else if (gst_structure_get_clock_time(message_structure, "endtime", &timestamp))
		{
			waittime = timestamp;
		}

		// delay message
		if (GST_CLOCK_TIME_IS_VALID(waittime))
		{
			GstClockTime basetime = gst_element_get_base_time(spectrum);
			GstClockID clock_id = gst_clock_new_single_shot_id(base_object->sync_clock, basetime+waittime);
			spectrum_message *mess = g_malloc(sizeof(spectrum_message));

			// set bands and threshold
			g_object_get(message_element, "bands", &(mess->bands), "threshold", &(mess->threshold), NULL);

			// set rate
			GstPad *sink = gst_element_get_static_pad(GST_ELEMENT(base_object->spectrum_element->obj), "sink");
			GstCaps *caps = gst_pad_get_negotiated_caps(sink);
			gst_object_unref(sink);

			GstStructure *caps_structure = gst_caps_get_structure(caps, 0);
			gst_structure_get_int(caps_structure, "rate", &(mess->rate));
			gst_caps_unref(caps);

			// set magnitudes
			const GValue *list = gst_structure_get_value(message_structure, "magnitude");

			PyGILState_STATE gstate = PyGILState_Ensure();

			int i;
			mess->magnitudes = PyList_New(mess->bands);
			for (i=0; i < (mess->bands); i++)
			{
				const GValue *value = gst_value_list_get_value(list, i);
				gfloat f = g_value_get_float(value);
				PyList_SetItem(mess->magnitudes, i, Py_BuildValue("f", f));
			}

			PyGILState_Release(gstate);

			// set gobj
			GObject *gobj = (base_object->gobj).obj;
			g_assert(gobj != NULL);
			g_object_ref(gobj);
			mess->gobj = gobj;

			// delay message
			gst_clock_id_wait_async(clock_id, delayed_spectrum_update, mess);

			gst_clock_id_unref(clock_id);
		}
	}

	gst_object_unref(spectrum);
	gst_object_unref(message_element);

	return TRUE;
}

static int base_init(base *self, PyObject *args, PyObject *kwds)
{
	// call tp_init of PyGObject
	int args_len = PyTuple_Size(args);
	PyObject *reduced_args = PySequence_GetSlice(args, 2, args_len);
	if (PyGObject_Type->tp_init((PyObject *)self, reduced_args, kwds) < 0) return -1;
	Py_DECREF(reduced_args);

	// parse arguments
	if (!PyArg_ParseTuple(args, "O!O!", PyGObject_Type, &(self->spectrum_element), PyGObject_Type, &(self->pipeline))) return -1;

	// listen for spectrum messages
	GstBus *gstbus = gst_pipeline_get_bus(GST_PIPELINE(self->pipeline->obj));
	g_assert(gstbus != NULL);
	gst_bus_add_signal_watch(gstbus);
	Py_INCREF(self);
	g_signal_connect(G_OBJECT(gstbus), "message::element", G_CALLBACK(on_message), self);
	gst_object_unref(gstbus);

	// get clock of pipeline
	self->sync_clock = gst_pipeline_get_clock(GST_PIPELINE(self->pipeline->obj));
	g_assert(self->sync_clock != NULL);

	return 0;
}

PyMODINIT_FUNC initSpectrumData(void)
{
	init_pygobject();

	// get gobject_module for GObject type and for registering signals
	PyObject *gobject_module = PyImport_ImportModule("gobject");

	// get GObject type to be able to use it as parent class
	PyGObject_Type = (PyTypeObject*)PyObject_GetAttrString(gobject_module, "GObject");

	// create "base" type
	baseType.tp_base = PyGObject_Type; // inherit from GObject
	baseType.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE;
	baseType.tp_init = (initproc)base_init;
	baseType.tp_members = base_members;
	baseType.tp_doc = "SpectrumData base class";

	if (PyType_Ready(&baseType)<0) return;

	// add "magnitudes-available" signal to "base" type
	// (see http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm, "Creating your own signals")
	PyObject *type_int = PyObject_GetAttrString(gobject_module, "TYPE_INT");
	PyObject *type_pyobject = PyObject_GetAttrString(gobject_module, "TYPE_PYOBJECT");
	PyObject *signal_args = PyTuple_Pack(4, type_int, type_int, type_int, type_pyobject);
	Py_DECREF(type_int);
	Py_DECREF(type_pyobject);

	PyObject *type_none = PyObject_GetAttrString(gobject_module, "TYPE_NONE");
	PyObject *run_first = PyObject_GetAttrString(gobject_module, "SIGNAL_RUN_FIRST");
	PyObject *tuple = PyTuple_Pack(3,
		run_first,
		type_none,
		signal_args
	);
	Py_DECREF(run_first);
	Py_DECREF(type_none);
	Py_DECREF(signal_args);

	PyObject *dict = PyDict_New();
	PyDict_SetItemString(dict, "magnitudes_available", tuple);
	Py_DECREF(tuple);

	PyDict_SetItemString(baseType.tp_dict, "__gsignals__", dict);
	Py_DECREF(dict);

	PyObject *type_register = PyObject_GetAttrString(gobject_module, "type_register");
	PyObject *type_register_args = PyTuple_Pack(1, (PyObject*)&baseType);
	PyObject_CallObject(type_register, type_register_args);
	Py_DECREF(type_register);
	Py_DECREF(type_register_args);

	// don't need gobject_module anymore
	Py_DECREF(gobject_module);

	// add "base" class to "SpectrumData" module
	PyObject *module = Py_InitModule3("SpectrumData", NULL, "Module containing SpectrumData base class");
	Py_INCREF(&baseType);
	PyModule_AddObject(module, "base", (PyObject*)&baseType);
}
