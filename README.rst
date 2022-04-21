..
    Copyright (C) 2019 CERN.
    Copyright (C) 2019 Northwestern University.


    Invenio-RDM-Records is free software; you can redistribute it and/or
    modify it under the terms of the MIT License; see LICENSE file for more
    details.

====================
 Invenio-RDM-Records
====================

.. image:: https://github.com/geo-knowledge-hub/invenio-rdm-records/workflows/CI/badge.svg
        :target: https://github.com/geo-knowledge-hub/invenio-rdm-records/actions?query=workflow%3ACI+branch%3Amaster

.. image:: https://img.shields.io/github/tag/geo-knowledge-hub/invenio-rdm-records.svg
        :target: https://github.com/geo-knowledge-hub/invenio-rdm-records/releases

.. image:: https://img.shields.io/github/license/geo-knowledge-hub/invenio-rdm-records.svg
        :target: https://github.com/geo-knowledge-hub/invenio-rdm-records/blob/master/LICENSE

DataCite-based data model for Invenio.

About
======

This repository is a fork from the `Invenio RDM Records <https://github.com/inveniosoftware/invenio-rdm-records>`_ package developed by the `Invenio Team <https://github.com/inveniosoftware>`_. This fork incorporates GEO Knowledge Hub-specific features and modifications to the original package.

We thank the `Invenio Team <https://github.com/inveniosoftware>`_ for making this mature software available to the entire community.

Development
===========

Install
-------

Choose a version of elasticsearch and a DB, then run:

.. code-block:: console

    pip install -e .
    pip install invenio-search[elasticsearch7]
    pip install invenio-db[<[mysql|postgresql|]>,versioning]


Tests
-----

.. code-block:: console

    pip install -e .[tests]
    ./run-tests.sh
