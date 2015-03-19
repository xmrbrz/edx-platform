;(function (define, undefined) {
    'use strict';
    define([
        'gettext', 'underscore', 'backbone',
    ], function (gettext, _, Backbone) {

        var AccountSettingsModel = Backbone.Model.extend({
            idAttribute: 'username',
            defaults: {
                username: '',
                name: '',
                email: '',
                password: '',
                language: null,
                country: null,
                date_joined: "",
                gender: null,
                goals: "",
                level_of_education: null,
                mailing_address: "",
                year_of_birth: null,
                bio: null
            },

            parse : function(response, xhr) {
                if (_.isNull(response)) {
                    return {};
                }

                // Currently when a non-staff user access someone else profile, there is no direct information
                // present to determine the profile visibility/privacy configuration/settings.
                // So here we will try to guess a user's profile privacy settings
                // The approach is simple, We will check the fields according to ACCOUNT_VISIBILITY_CONFIGURATION
                // and set `profilePrivacy` attribute on model
                var isEqual = function (receivedFields, neededFields) {
                    if (receivedFields.length != neededFields.length) {
                        return false;
                    }
                    return _.all(receivedFields, function(f) {
                        return _.include(neededFields, f);
                    });
                };

                var _private = isEqual(
                    _.keys(response),
                    ['username', 'profile_image']
                );

                var privacyAttribute = {};
                privacyAttribute['profilePrivacy'] = _private ? 'private': 'all_users';
                this.set(privacyAttribute, { silent: true });

  	            return response;
            }
        });

        return AccountSettingsModel;
    })
}).call(this, define || RequireJS.define);
