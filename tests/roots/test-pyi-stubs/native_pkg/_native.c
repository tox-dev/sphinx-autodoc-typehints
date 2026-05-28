/* Mirrors the PyO3 native-submodule shape from discussion #698:
 * ``native_pkg.warc`` is built via ``PyModule_New`` and registered in ``sys.modules`` with no
 * ``__file__`` / ``__spec__`` / ``__path__``.
 */

#include <Python.h>

static PyObject *parse(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    Py_RETURN_NONE;
}

static PyObject *raw_parse(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    Py_RETURN_NONE;
}

/* ``parse`` uses the PyO3-style Argument Clinic header (recoverable signature);
 * ``raw_parse`` omits it so we cover the no-signature path. */
static PyMethodDef warc_methods[] = {
    {"parse", parse, METH_VARARGS,
     "parse($module, data)\n--\n\nParse WARC records.\n\n:param data: input bytes"},
    {"raw_parse", raw_parse, METH_VARARGS,
     "Parse WARC records.\n\n:param data: input bytes"},
    {NULL, NULL, 0, NULL}
};

static PyTypeObject WarcRecordType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "native_pkg.warc.WarcRecord",
    .tp_doc = "A WARC record (native).",
    .tp_basicsize = sizeof(PyObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = PyType_GenericNew,
};

static int register_warc_submodule(PyObject *parent) {
    PyObject *warc = PyModule_New("native_pkg.warc");
    if (warc == NULL) {
        return -1;
    }

    if (PyType_Ready(&WarcRecordType) < 0) {
        Py_DECREF(warc);
        return -1;
    }
    Py_INCREF(&WarcRecordType);
    if (PyModule_AddObject(warc, "WarcRecord", (PyObject *)&WarcRecordType) < 0) {
        Py_DECREF(&WarcRecordType);
        Py_DECREF(warc);
        return -1;
    }

    if (PyModule_AddFunctions(warc, warc_methods) < 0) {
        Py_DECREF(warc);
        return -1;
    }

    Py_INCREF(warc);
    if (PyModule_AddObject(parent, "warc", warc) < 0) {
        Py_DECREF(warc);
        Py_DECREF(warc);
        return -1;
    }

    PyObject *sys_modules = PyImport_GetModuleDict();
    if (sys_modules == NULL) {
        Py_DECREF(warc);
        return -1;
    }
    if (PyDict_SetItemString(sys_modules, "native_pkg.warc", warc) < 0) {
        Py_DECREF(warc);
        return -1;
    }
    Py_DECREF(warc);
    return 0;
}

static int native_exec(PyObject *m) {
    return register_warc_submodule(m);
}

static PyModuleDef_Slot native_slots[] = {
    {Py_mod_exec, native_exec},
#ifdef Py_mod_gil
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
    {0, NULL}
};

static struct PyModuleDef native_module = {
    PyModuleDef_HEAD_INIT,
    "native_pkg._native",
    NULL,
    0,
    NULL,
    native_slots,
    NULL,
    NULL,
    NULL
};

PyMODINIT_FUNC PyInit__native(void) {
    return PyModuleDef_Init(&native_module);
}
