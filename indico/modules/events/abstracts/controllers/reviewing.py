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

from flask import request, session
from werkzeug.exceptions import Forbidden

from indico.modules.events.abstracts.controllers.base import AbstractMixin
from indico.modules.events.abstracts.forms import AbstractJudgmentForm
from indico.modules.events.abstracts.models.files import AbstractFile
from indico.modules.events.abstracts.models.reviews import AbstractReview
from indico.modules.events.abstracts.models.review_ratings import AbstractReviewRating
from indico.modules.events.abstracts.operations import judge_abstract
from indico.modules.events.abstracts.util import make_review_form
from indico.modules.events.abstracts.views import WPManageAbstracts
from indico.modules.events.tracks.models.tracks import Track
from indico.web.flask.templating import get_template_module
from indico.web.forms.base import FormDefaults

from indico.web.util import jsonify_data

from MaKaC.webinterface.rh.conferenceDisplay import RHConferenceBaseDisplay


class RHAbstractReviewBase(AbstractMixin, RHConferenceBaseDisplay):

    def _checkProtection(self):
        RHConferenceBaseDisplay._checkProtection(self)
        AbstractMixin._checkProtection(self)

    def _checkParams(self, params):
        RHConferenceBaseDisplay._checkParams(self, params)
        AbstractMixin._checkParams(self)


class RHAbstractsDownloadAttachment(RHAbstractReviewBase):
    """Download an attachment file belonging to an abstract."""

    normalize_url_spec = {
        'locators': {
            lambda self: self.abstract_file
        }
    }

    def _checkParams(self, params):
        RHAbstractReviewBase._checkParams(self, params)
        self.abstract_file = AbstractFile.get_one(request.view_args['file_id'])

    def _process(self):
        return self.abstract_file.send()


def get_user_review_for_track(user, abstract, track):
    results = [review for review in abstract.get_track_reviews(track) if review.user == user]
    assert len(results) <= 1
    return results[0] if results else None


def build_review_form(abstract, track):
    review_form_class = make_review_form(abstract.event_new)
    review_for_track = get_user_review_for_track(session.user, abstract, track)

    if review_for_track:
        answers = {'question_{}'.format(rating.question.id): rating.value
                   for rating in review_for_track.ratings}
        defaults = FormDefaults(obj=review_for_track, **answers)
    else:
        defaults = FormDefaults()

    return review_form_class(prefix="track-{}".format(track.id), obj=defaults)


class AbstractPageMixin(AbstractMixin):
    """Display abstract management page"""

    def _process(self):
        review_forms = {track.id: build_review_form(self.abstract, track)
                        for track in self.abstract.reviewed_for_tracks
                        if track.is_user_reviewer(session.user)}
        judgement_form = AbstractJudgmentForm(abstract=self.abstract)

        return WPManageAbstracts.render_template('abstract.html', self._conf, abstract=self.abstract,
                                                 judgement_form=judgement_form, review_forms=review_forms,
                                                 management=self.management)


class RHJudgeAbstract(RHAbstractReviewBase):
    CSRF_ENABLED = True

    def _process(self):
        form = AbstractJudgmentForm(abstract=self.abstract)
        if form.process_ajax():
            return form.ajax_response
        elif form.validate_on_submit():
            judgment_data, abstract_data = form.split_data
            judge_abstract(self.abstract, abstract_data, judge=session.user, **judgment_data)
        tpl = get_template_module('events/abstracts/abstract/judge.html')
        return jsonify_data(html=tpl.render_decision_box(self.abstract, form))


class RHReviewAbstractForTrack(RHAbstractReviewBase):
    CSRF_ENABLED = True

    normalize_url_spec = {
        'locators': {
            lambda self: self.abstract
        },
        'preserved_args': {'track_id'}
    }

    def _checkProtection(self):
        if not self.abstract.can_review(session.user):
            raise Forbidden
        RHAbstractReviewBase._checkProtection(self)

    def _checkParams(self, params):
        RHAbstractReviewBase._checkParams(self, params)
        self.track = Track.get_one(request.view_args['track_id'])
        self.review = get_user_review_for_track(session.user, self.abstract, self.track)

    def _process(self):
        form = build_review_form(self.abstract, self.track)

        if form.validate_on_submit():
            if self.review:
                form.populate_obj(self.review)
                for question in self.event_new.abstract_review_questions:
                    rating = question.get_review_rating(self.review)
                    if not rating:
                        rating = AbstractReviewRating(question=question, review=self.review)
                    rating.value = form.data["question_{}".format(question.id)]
            else:
                self.review = AbstractReview(abstract=self.abstract, track=self.track, user=session.user)
                form.populate_obj(self.review)
                for question in self.event_new.abstract_review_questions:
                    self.review.ratings.append(
                        AbstractReviewRating(question=question, value=form.data["question_{}".format(question.id)]))
        tpl = get_template_module('events/abstracts/abstract/review.html')
        return jsonify_data(html=tpl.render_review_box(form, self.abstract, self.track))
