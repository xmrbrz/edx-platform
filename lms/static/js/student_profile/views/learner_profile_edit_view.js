;(function (define, undefined) {
    'use strict';
    define([
        'gettext', 'jquery', 'underscore', 'backbone'
    ], function (gettext, $, _, Backbone) {

        var LearnerProfileEditView = Backbone.View.extend({

            events: {
                'change .profile-visibility-select': 'setProfileVisibility'
            },

            initialize: function (options) {
                this.template = _.template($('#learner_profile_edit-tpl').text());
            },

            render: function () {
                this.$el.html(this.template({
                    info: this.options.info,
                    accountSettingsPageUrl: this.options.accountSettingsPageUrl,
                    username: this.options.model.get('username'),
                    profileIsPublic: this.getProfileVisibility() == 'all_users',
                    showBirthYearMessage: _.isNull(this.options.model.get('year_of_birth')),
                    readonly: this.options.info.readonly
                }));
                this.renderFields();
                this.setViewAsReadonly();
                return this;
            },

            renderFields: function() {
                var view = this;

                this.$('.profile-fields-section-one').append(this.options.usernameFieldView.render().el);

                if (this.getProfileVisibility() == 'all_users') {
                    _.each(this.options.sectionOneFieldViews, function (fieldView, index) {
                        fieldView.undelegateEvents();
                        view.$('.profile-fields-section-one').append(fieldView.render().el);
                        fieldView.delegateEvents();
                    });

                    _.each(this.options.sectionTwoFieldViews, function (fieldView, index) {
                        fieldView.undelegateEvents();
                        view.$('.profile-fields-section-two').append(fieldView.render().el);
                        fieldView.delegateEvents();
                    });
                }
            },

            getProfileVisibility: function () {
                if (this.options.info.has_preferences_access) {
                    return this.options.preferencesModel.get('account_privacy');
                } else {
                    return this.model.get('profilePrivacy');
                }
            },

            setProfileVisibility: function (event) {
                var self = this;
                var options = {
                    contentType: 'application/merge-patch+json',
                    patch: true,
                    wait: true
                };
                this.options.preferencesModel.save(
                    {account_privacy: this.getSelectedVisibilityValue()},
                    options
                ).done( function () {
                    self.render();
                });
            },

            getSelectedVisibilityValue: function () {
                return this.$('.profile-visibility-select').val();
            },

            setViewAsReadonly: function () {
                if (this.options.info.readonly) {
                    this.$('.account-settings-field-country').addClass('profile-data-set-state').addClass('profile-visibility-readonly');
                    this.$('.account-settings-field-language').addClass('profile-data-set-state').addClass('profile-visibility-readonly');
                    this.$('.account-settings-field-bio').addClass('profile-data-set-state').addClass('profile-visibility-readonly');
                }
            }
        });

        return LearnerProfileEditView;
    })
}).call(this, define || RequireJS.define);