#include <pyhelpers.hpp>
#include <cmath>
#define DEG2RAD 0.017453292519943295
#define RAD2DEG 57.29577951308232

//calculate lateral distance between birds and aircraft
inline double kwik_ac_birds(const double& lat0, const double& lon0, const double& lat1, const double& lon1)
{
    const double Re = 6371000.0;
    const double coslat = 0.6236170235827863; // cos(51.4192475)
    double dx = Re * (lon1 - lon0) * coslat;
    double dy = Re * (lat1 - lat0);
    return sqrt(dx*dx + dy*dy);
};

// calculates bearing between birds and aircraft, i.e. the pacman function
inline double pacman(const double& lat0, const double& lon0, const double& lat1, const double& lon1)
{
    double dlon = lon1 - lon0;
    double coslat1 = cos(lat1);
    // 2DO RIGHT FUNCTION NAMES???
    double bear = atan2(sin(dlon) * coslat1,
		cos(lat0) * sin(lat1) - sin(lat0) * coslat1 * cos(dlon));

    // revert to degrees and normalize to range 0 to 360
    return fmod((bear * RAD2DEG + 360.0), 360.0);
}

static PyObject* cddetect_birds(PyObject* self, PyObject* args)
{
    PyObject *birds = NULL,
             *traf = NULL;

    double simt = 0.0;

    if (!PyArg_ParseTuple(args, "OOd", &birds, &traf, &simt))
        return NULL;
    PyDoubleArrayAttr lat_ac(traf, "lat_ac"), lon_ac(traf, "lon_ac"), alt_ac(traf, "alt_ac"),
                        collision_height(traf, "collision_height"), collision_radius_ac(traf, "collision_radius_ac"),
                        hdg(traf, "hdg"), sweep(traf, "sweep"),
                        lat_birds(birds, "lat_birds"), lon_birds(birds, "lon_birds"), alt_birds(birds, "alt_birds"),
                        collision_radius_birds(birds, "collision_radius_birds");

    // Only continue if all arrays exist
    if (lat_ac && lon_ac && alt_ac && lat_birds && lon_birds && alt_birds)
    {
        // Return lists
        PyListAttr nm_idx_ac, nm_idx_birds, coll_idx_ac, coll_idx_birds;
        // Get size of birds and ac
        npy_intp  size_ac    = lat_ac.size(),
                  size_birds  = lat_birds.size();

        double rlat_ac, rlon_ac, rlat_bird, rlon_bird;
        // first: test whether bird and aircraft are within the same altitude band
        for (int i = 0; i < size_ac; ++i) {
            lat_birds.ptr = lat_birds.ptr_start;
            lon_birds.ptr = lon_birds.ptr_start;
            alt_birds.ptr = alt_birds.ptr_start;
            collision_radius_birds.ptr = collision_radius_birds.ptr_start;
            rlat_ac = *lat_ac.ptr * DEG2RAD;
            rlon_ac = *lon_ac.ptr * DEG2RAD;
            for (int j = 0; j < size_birds; ++j) {

                if(*collision_height.ptr < fabs(*alt_ac.ptr - *alt_birds.ptr))
                {
                    rlat_bird = *lat_birds.ptr * DEG2RAD;
                    rlon_bird = *lon_birds.ptr * DEG2RAD;
                    // if vertical distance is dangerous, test for lateral distance
                    // for nearmisses first. 2DO WHERE TO PUT THE 50M
                    double dist = kwik_ac_birds(rlat_ac, rlon_ac, rlat_bird, rlon_bird);
                    if(dist < 50.0)
                    {
                        nm_idx_ac.append(int(i));
                        nm_idx_birds.append(int(j));

                        // after checking for near misses, check for collisions
                        // first for lateral distance, then for pacman
                        if(dist < collision_radius_ac+ collision_radius_birds)
                        {
                            // check for pacman
            				double bear_ac_birds = pacman(rlat_ac, rlon_ac, rlat_bird, rlon_bird);

            				double pacman_high = (90.0 + *sweep.ptr);
            				double pacman_low  = (90.0 - *sweep.ptr);

            				double delta_hdg = fmod(fmod(*hdg.ptr - bear_ac_birds, 360.0) + 180. + 360.0, 360.) - 180.0;

            				if( (delta_hdg > pacman_low) && (delta_hdg < pacman_high))
            				{
                                coll_idx_ac.append(int(i));
                                coll_idx_birds.append(int(j));
            				}
                        }
                    }
                }
                ++lat_birds.ptr; ++lon_birds.ptr; ++alt_birds.ptr; collision_radius_birds.ptr++;
            }
            ++lat_ac.ptr; ++lon_ac.ptr; ++alt_ac.ptr;
            ++collision_height.ptr; ++collision_radius_ac.ptr;
            ++hdg.ptr; ++sweep.ptr;
        }
        return Py_BuildValue("OOOO", nm_idx_ac.attr, nm_idx_birds.attr, coll_idx_ac.attr, coll_idx_birds.attr);
    }
    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef methods[] = {
    {"detect_birdstrikes", cddetect_birds, METH_VARARGS, "Detect birdstrikes and near-misses."},
    {NULL}  /* Sentinel */
};

#ifndef PyMODINIT_FUNC  /* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef cbirdsdef =
{
    PyModuleDef_HEAD_INIT,
    "cbirds",    /* name of module */
    "",          /* module documentation, may be NULL */
    -1,          /* size of per-interpreter state of the module, or -1 if the module keeps state in global variables. */
    methods
};

PyMODINIT_FUNC PyInit_cbirds(void)
{
    import_array();
    return PyModule_Create(&cbirdsdef);
};
#else
PyMODINIT_FUNC initcbirds(void)
{
    Py_InitModule("cbirds", methods);
    import_array();
};
#endif
