# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2021 CERN.
# Copyright (C) 2020-2021 Northwestern University.
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""RDM record schemas."""

from marshmallow import Schema
from marshmallow_utils.fields import SanitizedUnicode


class PIDSchema(Schema):
    """PIDs schema."""

    identifier = SanitizedUnicode(required=True)
    provider = SanitizedUnicode(required=True)
    client = SanitizedUnicode()
