# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2021 CERN.
# Copyright (C) 2020-2021 Northwestern University.
# Copyright (C) 2021 TU Wien.
# Copyright (C) 2021 Graz University of Technology.
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""RDM Record Service."""

import arrow
from invenio_drafts_resources.services.records import RecordService
from invenio_records_resources.services.uow import RecordCommitOp, unit_of_work

from invenio_rdm_records.services.errors import EmbargoNotLiftedError


class RDMRecordService(RecordService):
    """RDM record service."""

    def __init__(self, config, files_service=None, draft_files_service=None,
                 secret_links_service=None, pids_service=None,
                 review_service=None):
        """Constructor for RecordService."""
        super().__init__(config, files_service, draft_files_service)
        self._secret_links = secret_links_service
        self._pids = pids_service
        self._review = review_service

    #
    # Subservices
    #
    @property
    def secret_links(self):
        """Record secret link service."""
        return self._secret_links

    @property
    def pids(self):
        """Record PIDs service."""
        return self._pids

    @property
    def review(self):
        """Record PIDs service."""
        return self._review

    #
    # Service methods
    #
    @unit_of_work()
    def lift_embargo(self, identity, _id, uow=None):
        """Lifts embargo from the record and draft (if exists).

        It's an error if you try to lift an embargo that has not yet expired.
        Use this method in combination with scan_expired_embargos().
        """
        # Get the record
        record = self.record_cls.pid.resolve(_id)

        # Check permissions
        self.require_permission(identity, "lift_embargo", record=record)

        # Modify draft embargo if draft exists and it's the same as the record.
        draft = None
        if record.has_draft:
            draft = self.draft_cls.pid.resolve(_id, registered_only=False)
            if record.access == draft.access:
                if not draft.access.lift_embargo():
                    raise EmbargoNotLiftedError(_id)
                uow.register(RecordCommitOp(draft, indexer=self.indexer))

        if not record.access.lift_embargo():
            raise EmbargoNotLiftedError(_id)

        uow.register(RecordCommitOp(record, indexer=self.indexer))

    def scan_expired_embargos(self, identity):
        """Scan for records with an expired embargo."""
        today = arrow.utcnow().date().isoformat()

        embargoed_q = \
            f"access.embargo.active:true " \
            f"AND access.embargo.until:[* TO {today}]"

        return self.scan(identity=identity, q=embargoed_q)
