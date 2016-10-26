# This file is part of Indico.
# Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from indico.modules.events.abstracts.controllers.reviewing import AbstractPageMixin
from indico.util.fs import secure_filename
from indico.web.flask.util import send_file
from MaKaC.PDFinterface.conference import AbstractToPDF
from MaKaC.webinterface.rh.conferenceDisplay import RHConferenceBaseDisplay


class RHDisplayAbstract(AbstractPageMixin, RHConferenceBaseDisplay):
    management = False

    def _checkParams(self, params):
        RHConferenceBaseDisplay._checkParams(self, params)
        AbstractPageMixin._checkParams(self)

    def _checkProtection(self):
        RHConferenceBaseDisplay._checkProtection(self)
        AbstractPageMixin._checkProtection(self)


class RHDisplayAbstractExportPDF(RHDisplayAbstract):
    def _process(self):
        pdf = AbstractToPDF(self.abstract)
        file_name = secure_filename('abstract-{}.pdf'.format(self.abstract.friendly_id), 'abstract.pdf')
        return send_file(file_name, pdf.generate(), 'application/pdf')
