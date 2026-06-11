#include <Python.h>

static PyObject *greet(PyObject *self, PyObject *args) {
    const char *name;
    if (!PyArg_ParseTuple(args, "s", &name))
        return NULL;
    return PyUnicode_FromFormat("Hello, %s!", name);
}

static PyObject *with_hook(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    Py_RETURN_NONE;
}

static PyObject *encoder_new(PyTypeObject *type, PyObject *args, PyObject *kwargs) {
    (void)args;
    (void)kwargs;
    return type->tp_alloc(type, 0);
}

static PyObject *encoder_get_depth(PyObject *self, void *closure) {
    (void)self;
    (void)closure;
    return PyLong_FromLong(0);
}

static PyObject *encoder_get_hook(PyObject *self, void *closure) {
    (void)self;
    (void)closure;
    Py_RETURN_NONE;
}

static PyGetSetDef encoder_getset[] = {
    {"depth", encoder_get_depth, NULL, "current nesting depth", NULL},
    {"hook", encoder_get_hook, NULL, "the active encoder hook", NULL},
    {"flags", encoder_get_depth, NULL, "encoder behavior flags", NULL},
    {NULL, NULL, NULL, NULL, NULL}
};

static PyTypeObject EncoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "c_ext_mod.Encoder",
    .tp_doc = "Encoder class",
    .tp_basicsize = sizeof(PyObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = encoder_new,
    .tp_getset = encoder_getset,
};

static int module_exec(PyObject *m) {
    if (PyType_Ready(&EncoderType) < 0)
        return -1;

    Py_INCREF(&EncoderType);
    if (PyModule_AddObject(m, "Encoder", (PyObject *)&EncoderType) < 0) {
        Py_DECREF(&EncoderType);
        return -1;
    }

    return 0;
}

static PyMethodDef methods[] = {
    {"greet", greet, METH_VARARGS, NULL},
    {"with_hook", with_hook, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};

static PyModuleDef_Slot module_slots[] = {
    {Py_mod_exec, module_exec},
#ifdef Py_mod_gil
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
    {0, NULL}
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "c_ext_mod",
    NULL,
    0,
    methods,
    module_slots,
    NULL,
    NULL,
    NULL
};

PyMODINIT_FUNC PyInit_c_ext_mod(void) {
    return PyModuleDef_Init(&module);
}
