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

static PyMethodDef methods[] = {
    {"greet", greet, METH_VARARGS, NULL},
    {"with_hook", with_hook, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};

static PyModuleDef_Slot module_slots[] = {
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
