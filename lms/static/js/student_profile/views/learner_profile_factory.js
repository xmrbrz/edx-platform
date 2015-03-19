;(function (define, undefined) {
    'use strict';
    define([
        'gettext', 'jquery', 'underscore', 'backbone',
        'js/student_account/models/account_settings_models',
        'js/student_profile/models/learner_profile_preferences_model',
        'js/student_profile/views/learner_profile_edit_view',
        'js/student_account/views/account_settings_fields'
    ], function (gettext, $, _, Backbone, AccountSettingsModel, LearnerProfilePreferencesModel, LearnerProfileEditView,
                 AccountSettingsFieldViews) {

        var setupLearnerProfile = function (info) {

            var learnerProfileElement = $('.learner-profile-container');

            var learnerProfilePreferencesModel = new LearnerProfilePreferencesModel();
            learnerProfilePreferencesModel.url = learnerProfileElement.data('preferences-api-url');

            var accountSettingsModel = new AccountSettingsModel();
            accountSettingsModel.url = learnerProfileElement.data('accounts-api-url');

            var usernameFieldView = new AccountSettingsFieldViews.ReadonlyFieldView({
                    model: accountSettingsModel,
                    valueAttribute: "username",
                    helpMessage: ""
            });

            var sectionOneFieldViews = [
                 new AccountSettingsFieldViews.DropdownFieldView({
                    model: accountSettingsModel,
                    valueAttribute: "country",
                    required: false,
                    helpMessage: '',
                    options: info['country_options'],
                    iconName: 'fa-map-marker',
                    alwaysEditable: false,
                    showMessages: false,
                    placeholderValue: 'Add country'
                }),

                new AccountSettingsFieldViews.DropdownFieldView({
                    model: accountSettingsModel,
                    valueAttribute: "language",
                    required: false,
                    helpMessage: '',
                    options: info['language_options'],
                    iconName: 'fa-comment fa-flip-horizontal',
                    alwaysEditable: false,
                    showMessages: false,
                    placeholderValue: 'Add language'
                })
            ];

            var sectionTwoFieldViews = [
                new AccountSettingsFieldViews.TextareaFieldView({
                    model: accountSettingsModel,
                    title: 'About Me',
                    valueAttribute: "bio",
                    helpMessage: '',
                    showMessages: false,
                    placeholderValue: "Tell other edX learners a little about yourself, where you're from, what your interests are ,why you joined edX, what you hope to learn..."
                })
            ];

            accountSettingsModel.fetch().done(function () {
                learnerProfilePreferencesModel.fetch({complete: function () {
                    new LearnerProfileEditView({
                        el: learnerProfileElement,
                        model: accountSettingsModel,
                        preferencesModel: learnerProfilePreferencesModel,
                        accountSettingsPageUrl: learnerProfileElement.data('account-settings-page-url'),
                        info: info,
                        usernameFieldView: usernameFieldView,
                        sectionOneFieldViews: sectionOneFieldViews,
                        sectionTwoFieldViews: sectionTwoFieldViews
                    }).render();
                }});
            });
        };

        return setupLearnerProfile;
    })
}).call(this, define || RequireJS.define);