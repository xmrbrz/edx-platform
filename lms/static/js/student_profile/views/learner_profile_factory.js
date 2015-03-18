;(function (define, undefined) {
    'use strict';
    define([
        'gettext', 'jquery', 'underscore', 'backbone',
        'js/student_account/models/account_settings_models',
        'js/student_profile/models/learner_profile_preferences_model',
        'js/student_profile/views/learner_profile_view'
    ], function (gettext, $, _, Backbone, AccountSettingsModel, LearnerProfilePreferencesModel, LearnerProfileView) {

        var setupLearnerProfile = function (info) {

            var learnerProfileElement = $('.learner-profile-container');
            var learnerProfilePreferencesModel = new LearnerProfilePreferencesModel();
            learnerProfilePreferencesModel.url = learnerProfileElement.data('preferences-api-url');
            var accountSettingModel = new AccountSettingsModel();
            accountSettingModel.url = learnerProfileElement.data('accounts-api-url');

            var learnerProfileView = new LearnerProfileView({
                el: learnerProfileElement,
                model: accountSettingModel,
                preferencesModel: learnerProfilePreferencesModel,
                accountSettingsPageUrl: learnerProfileElement.data('account-settings-page-url'),
                info: info
            });

            accountSettingModel.fetch().done(function () {
                learnerProfilePreferencesModel.fetch({
                    complete: function () {learnerProfileView.render()}
                });
            });
        };

        return setupLearnerProfile;
    })
}).call(this, define || RequireJS.define);