"""
unittests for xmodule

Run like this:

    paver test_lib -l common/lib/xmodule

"""

import json
import os
import pprint
import unittest
import inspect
import mock

from contextlib import contextmanager
from lazy import lazy
from mock import Mock
from operator import attrgetter
from path import path
from eventtracking import tracker
from eventtracking.django import DjangoTracker


from xblock.field_data import DictFieldData
from xblock.fields import ScopeIds, Scope, Reference, ReferenceList, ReferenceValueDict

from xmodule.x_module import ModuleSystem, XModuleDescriptor, XModuleMixin
from xmodule.modulestore.inheritance import InheritanceMixin, own_metadata
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from xmodule.mako_module import MakoDescriptorSystem
from xmodule.error_module import ErrorDescriptor
from xmodule.assetstore import AssetMetadata
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.mongo.draft import DraftModuleStore
from xmodule.modulestore.xml import CourseLocationManager
from xmodule.modulestore.draft_and_published import DIRECT_ONLY_CATEGORIES, ModuleStoreDraftAndPublished


MODULE_DIR = path(__file__).dirname()
# Location of common test DATA directory
# '../../../../edx-platform/common/test/data/'
DATA_DIR = MODULE_DIR.parent.parent.parent.parent / "test" / "data"


open_ended_grading_interface = {
    'url': 'blah/',
    'username': 'incorrect_user',
    'password': 'incorrect_pass',
    'staff_grading': 'staff_grading',
    'peer_grading': 'peer_grading',
    'grading_controller': 'grading_controller',
}


class TestModuleSystem(ModuleSystem):  # pylint: disable=abstract-method
    """
    ModuleSystem for testing
    """
    @mock.patch('eventtracking.tracker.emit')
    def __init__(self, mock_emit, **kwargs):  # pylint: disable=unused-argument
        id_manager = CourseLocationManager(kwargs['course_id'])
        kwargs.setdefault('id_reader', id_manager)
        kwargs.setdefault('id_generator', id_manager)
        kwargs.setdefault('services', {}).setdefault('field-data', DictFieldData({}))
        self.tracker = DjangoTracker()
        tracker.register_tracker(self.tracker)
        super(TestModuleSystem, self).__init__(**kwargs)

    def handler_url(self, block, handler, suffix='', query='', thirdparty=False):
        return '{usage_id}/{handler}{suffix}?{query}'.format(
            usage_id=unicode(block.scope_ids.usage_id),
            handler=handler,
            suffix=suffix,
            query=query,
        )

    def local_resource_url(self, block, uri):
        return 'resource/{usage_id}/{uri}'.format(
            usage_id=unicode(block.scope_ids.usage_id),
            uri=uri,
        )

    # Disable XBlockAsides in most tests
    def get_asides(self, block):
        return []


def get_test_system(course_id=SlashSeparatedCourseKey('org', 'course', 'run')):
    """
    Construct a test ModuleSystem instance.

    By default, the render_template() method simply returns the repr of the
    context it is passed.  You can override this behavior by monkey patching::

        system = get_test_system()
        system.render_template = my_render_func

    where `my_render_func` is a function of the form my_render_func(template, context).

    """
    user = Mock(name='get_test_system.user', is_staff=False)

    descriptor_system = get_test_descriptor_system()

    def get_module(descriptor):
        """Mocks module_system get_module function"""
        # pylint: disable=protected-access

        # Unlike XBlock Runtimes or DescriptorSystems,
        # each XModule is provided with a new ModuleSystem.
        # Construct one for the new XModule.
        module_system = get_test_system()

        # Descriptors can all share a single DescriptorSystem.
        # So, bind to the same one as the current descriptor.
        module_system.descriptor_runtime = descriptor._runtime  # pylint: disable=protected-access

        descriptor.bind_for_student(module_system, descriptor._field_data, user.id)

        return descriptor

    return TestModuleSystem(
        static_url='/static',
        track_function=Mock(name='get_test_system.track_function'),
        get_module=get_module,
        render_template=mock_render_template,
        replace_urls=str,
        user=user,
        get_real_user=lambda(__): user,
        filestore=Mock(name='get_test_system.filestore'),
        debug=True,
        hostname="edx.org",
        xqueue={
            'interface': None,
            'callback_url': '/',
            'default_queuename': 'testqueue',
            'waittime': 10,
            'construct_callback': Mock(name='get_test_system.xqueue.construct_callback', side_effect="/"),
        },
        node_path=os.environ.get("NODE_PATH", "/usr/local/lib/node_modules"),
        anonymous_student_id='student',
        open_ended_grading_interface=open_ended_grading_interface,
        course_id=course_id,
        error_descriptor_class=ErrorDescriptor,
        get_user_role=Mock(name='get_test_system.get_user_role', is_staff=False),
        user_location=Mock(name='get_test_system.user_location'),
        descriptor_runtime=descriptor_system,
    )


def get_test_descriptor_system():
    """
    Construct a test DescriptorSystem instance.
    """
    field_data = DictFieldData({})

    descriptor_system = MakoDescriptorSystem(
        load_item=Mock(name='get_test_descriptor_system.load_item'),
        resources_fs=Mock(name='get_test_descriptor_system.resources_fs'),
        error_tracker=Mock(name='get_test_descriptor_system.error_tracker'),
        render_template=mock_render_template,
        mixins=(InheritanceMixin, XModuleMixin),
        field_data=field_data,
        services={'field-data': field_data},
    )
    descriptor_system.get_asides = lambda block: []
    return descriptor_system


def mock_render_template(*args, **kwargs):
    """
    Pretty-print the args and kwargs.

    Allows us to not depend on any actual template rendering mechanism,
    while still returning a unicode object
    """
    return pprint.pformat((args, kwargs)).decode()


class ModelsTest(unittest.TestCase):
    def test_load_class(self):
        vc = XModuleDescriptor.load_class('video')
        vc_str = "<class 'xmodule.video_module.video_module.VideoDescriptor'>"
        self.assertEqual(str(vc), vc_str)


class LogicTest(unittest.TestCase):
    """Base class for testing xmodule logic."""
    descriptor_class = None
    raw_field_data = {}

    def setUp(self):
        super(LogicTest, self).setUp()
        self.system = get_test_system()
        self.descriptor = Mock(name="descriptor", url_name='', category='test')

        self.xmodule_class = self.descriptor_class.module_class
        usage_key = self.system.course_id.make_usage_key(self.descriptor.category, 'test_loc')
        # ScopeIds has 4 fields: user_id, block_type, def_id, usage_id
        scope_ids = ScopeIds(1, self.descriptor.category, usage_key, usage_key)
        self.xmodule = self.xmodule_class(
            self.descriptor, self.system, DictFieldData(self.raw_field_data), scope_ids
        )

    def ajax_request(self, dispatch, data):
        """Call Xmodule.handle_ajax."""
        return json.loads(self.xmodule.handle_ajax(dispatch, data))


def map_references(value, field, actual_course_key):
    """
    Map the references in value to actual_course_key and return value
    """
    if not value:  # if falsey
        return value
    if isinstance(field, Reference):
        return value.map_into_course(actual_course_key)
    if isinstance(field, ReferenceList):
        return [sub.map_into_course(actual_course_key) for sub in value]
    if isinstance(field, ReferenceValueDict):
        return {key: ele.map_into_course(actual_course_key) for key, ele in value.iteritems()}
    return value


class BulkAssertionManager(object):
    """
    This provides a facility for making a large number of assertions, and seeing all of
    the failures at once, rather than only seeing single failures.
    """
    def __init__(self, test_case):
        self._equal_assertions = []
        self._test_case = test_case

    def run_assertions(self):
        if len(self._equal_assertions) > 0:
            raise AssertionError(self._equal_assertions)


class BulkAssertionTest(unittest.TestCase):
    """
    This context manager provides a BulkAssertionManager to assert with,
    and then calls `run_assertions` at the end of the block to validate all
    of the assertions.
    """

    def setUp(self, *args, **kwargs):
        super(BulkAssertionTest, self).setUp(*args, **kwargs)
        self._manager = None

    @contextmanager
    def bulk_assertions(self):
        if self._manager:
            yield
        else:
            try:
                self._manager = BulkAssertionManager(self)
                yield
            finally:
                self._manager.run_assertions()
                self._manager = None

    def assertEqual(self, expected, actual, message=None):
        if self._manager is not None:
            try:
                super(BulkAssertionTest, self).assertEqual(expected, actual, message)
            except Exception as error:  # pylint: disable=broad-except
                exc_stack = inspect.stack()[1]
                if message is not None:
                    msg = '{} -> {}:{} -> {}'.format(message, exc_stack[1], exc_stack[2], unicode(error))
                else:
                    msg = '{}:{} -> {}'.format(exc_stack[1], exc_stack[2], unicode(error))
                self._manager._equal_assertions.append(msg)  # pylint: disable=protected-access
        else:
            super(BulkAssertionTest, self).assertEqual(expected, actual, message)
    assertEquals = assertEqual


class LazyFormat(object):
    """
    An stringy object that delays formatting until it's put into a string context.
    """
    __slots__ = ('template', 'args', 'kwargs', '_message')

    def __init__(self, template, *args, **kwargs):
        self.template = template
        self.args = args
        self.kwargs = kwargs
        self._message = None

    def __unicode__(self):
        if self._message is None:
            self._message = self.template.format(*self.args, **self.kwargs)
        return self._message

    def __repr__(self):
        return unicode(self)


class CourseComparisonTest(BulkAssertionTest):
    """
    Mixin that has methods for comparing courses for equality.
    """

    def setUp(self):
        super(CourseComparisonTest, self).setUp()
        self.field_exclusions = set()
        self.ignored_asset_keys = set()

    def exclude_field(self, usage_id, field_name):
        """
        Mark field ``field_name`` of expected block usage ``usage_id`` as ignored

        Args:
            usage_id (:class:`opaque_keys.edx.UsageKey` or ``None``). If ``None``, skip, this field in all blocks
            field_name (string): The name of the field to skip
        """
        self.field_exclusions.add((usage_id, field_name))

    def ignore_asset_key(self, key_name):
        """
        Add an asset key to the list of keys to be ignored when comparing assets.

        Args:
            key_name: The name of the key to ignore.
        """
        self.ignored_asset_keys.add(key_name)

    def assertReferenceRelativelyEqual(self, reference_field, expected_block, actual_block):
        """
        Assert that the supplied reference field is identical on the expected_block and actual_block,
        assoming that the references are only relative (that is, comparing only on block_type and block_id,
        not course_key).
        """
        def extract_key(usage_key):
            if usage_key is None:
                return None
            else:
                return (usage_key.block_type, usage_key.block_id)
        expected = reference_field.read_from(expected_block)
        actual = reference_field.read_from(actual_block)
        if isinstance(reference_field, Reference):
            expected = extract_key(expected)
            actual = extract_key(actual)
        elif isinstance(reference_field, ReferenceList):
            expected = [extract_key(key) for key in expected]
            actual = [extract_key(key) for key in actual]
        elif isinstance(reference_field, ReferenceValueDict):
            expected = {key: extract_key(val) for (key, val) in expected.iteritems()}
            actual = {key: extract_key(val) for (key, val) in actual.iteritems()}
        self.assertEqual(
            expected,
            actual,
            LazyFormat(
                "Field {} doesn't match between usages {} and {}: {!r} != {!r}",
                reference_field.name,
                expected_block.scope_ids.usage_id,
                actual_block.scope_ids.usage_id,
                expected,
                actual
            )
        )

    def assertBlocksEqualByFields(self, expected_block, actual_block):
        self.assertEqual(expected_block.fields, actual_block.fields)
        for field in expected_block.fields.values():
            self.assertFieldEqual(field, expected_block, actual_block)

    def assertFieldEqual(self, field, expected_block, actual_block):
        if isinstance(field, (Reference, ReferenceList, ReferenceValueDict)):
            self.assertReferenceRelativelyEqual(field, expected_block, actual_block)
        else:
            expected = field.read_from(expected_block)
            actual = field.read_from(actual_block)
            self.assertEqual(
                expected,
                actual,
                LazyFormat(
                    "Field {} doesn't match between usages {} and {}: {!r} != {!r}",
                    field.name,
                    expected_block.scope_ids.usage_id,
                    actual_block.scope_ids.usage_id,
                    expected,
                    actual
                )
            )

    def assertCoursesEqual(self, expected_store, expected_course_key, actual_store, actual_course_key):
        """
        Assert that the courses identified by ``expected_course_key`` in ``expected_store`` and
        ``actual_course_key`` in ``actual_store`` are identical (ignore differences related
        owing to the course_keys being different).

        Any field value mentioned in ``self.field_exclusions`` by the key (usage_id, field_name)
        will be ignored for the purpose of equality checking.
        """
        # compare published
        with expected_store.branch_setting(ModuleStoreEnum.Branch.published_only, expected_course_key):
            with actual_store.branch_setting(ModuleStoreEnum.Branch.published_only, actual_course_key):
                expected_items = expected_store.get_items(expected_course_key, revision=ModuleStoreEnum.RevisionOption.published_only)
                actual_items = actual_store.get_items(actual_course_key, revision=ModuleStoreEnum.RevisionOption.published_only)
                self.assertGreater(len(expected_items), 0)
                self._assertCoursesEqual(expected_items, actual_items, actual_course_key)

        # if the modulestore supports having a draft branch
        if isinstance(expected_store, ModuleStoreDraftAndPublished):
            with expected_store.branch_setting(ModuleStoreEnum.Branch.draft_preferred, expected_course_key):
                with actual_store.branch_setting(ModuleStoreEnum.Branch.draft_preferred, actual_course_key):
                    # compare draft
                    if expected_store.get_modulestore_type(None) == ModuleStoreEnum.Type.split:
                        revision = ModuleStoreEnum.RevisionOption.draft_only
                    else:
                        revision = None
                    expected_items = expected_store.get_items(expected_course_key, revision=revision)
                    if actual_store.get_modulestore_type(None) == ModuleStoreEnum.Type.split:
                        revision = ModuleStoreEnum.RevisionOption.draft_only
                    else:
                        revision = None
                    actual_items = actual_store.get_items(actual_course_key, revision=revision)
                    self._assertCoursesEqual(expected_items, actual_items, actual_course_key, expect_drafts=True)

    def _assertCoursesEqual(self, expected_items, actual_items, actual_course_key, expect_drafts=False):
        with self.bulk_assertions():
            self.assertEqual(len(expected_items), len(actual_items))

            def map_key(usage_key):
                return (usage_key.block_type, usage_key.block_id)

            actual_item_map = {
                map_key(item.location): item
                for item in actual_items
            }

            for expected_item in expected_items:
                actual_item_location = actual_course_key.make_usage_key(expected_item.category, expected_item.location.block_id)
                # split and old mongo use different names for the course root but we don't know which
                # modulestore actual's come from here; so, assume old mongo and if that fails, assume split
                if expected_item.location.category == 'course':
                    actual_item_location = actual_item_location.replace(name=actual_item_location.run)
                actual_item = actual_item_map.get(map_key(actual_item_location))
                # must be split
                if actual_item is None and expected_item.location.category == 'course':
                    actual_item_location = actual_item_location.replace(name='course')
                    actual_item = actual_item_map.get(map_key(actual_item_location))

                # Formatting the message slows down tests of large courses significantly, so only do it if it would be used
                self.assertIsNotNone(actual_item, LazyFormat(u'cannot find {} in {}', map_key(actual_item_location), actual_item_map))

                # compare fields
                self.assertEqual(expected_item.fields, actual_item.fields)

                for field_name, field in expected_item.fields.iteritems():
                    if (expected_item.scope_ids.usage_id, field_name) in self.field_exclusions:
                        continue

                    if (None, field_name) in self.field_exclusions:
                        continue

                    # Children are handled specially
                    if field_name == 'children':
                        continue

                    self.assertFieldEqual(field, expected_item, actual_item)

                # compare children
                self.assertEqual(expected_item.has_children, actual_item.has_children)
                if expected_item.has_children:
                    expected_children = [
                        (expected_item_child.location.block_type, expected_item_child.location.block_id)
                        # get_children() rather than children to strip privates from public parents
                        for expected_item_child in expected_item.get_children()
                    ]
                    actual_children = [
                        (item_child.location.block_type, item_child.location.block_id)
                        # get_children() rather than children to strip privates from public parents
                        for item_child in actual_item.get_children()
                    ]
                    self.assertEqual(expected_children, actual_children)

    def assertAssetEqual(self, expected_course_key, expected_asset, actual_course_key, actual_asset):
        """
        Assert that two assets are equal, allowing for differences related to their being from different courses.
        """
        for key in self.ignored_asset_keys:
            if key in expected_asset:
                del expected_asset[key]
            if key in actual_asset:
                del actual_asset[key]

        expected_key = expected_asset.pop('asset_key')
        actual_key = actual_asset.pop('asset_key')
        self.assertEqual(expected_key.map_into_course(actual_course_key), actual_key)
        self.assertEqual(expected_key, actual_key.map_into_course(expected_course_key))

        expected_filename = expected_asset.pop('filename')
        actual_filename = actual_asset.pop('filename')
        self.assertEqual(expected_key.to_deprecated_string(), expected_filename)
        self.assertEqual(actual_key.to_deprecated_string(), actual_filename)
        self.assertEqual(expected_asset, actual_asset)

    def _assertAssetsEqual(self, expected_course_key, expected_assets, actual_course_key, actual_assets):  # pylint: disable=invalid-name
        """
        Private helper method for assertAssetsEqual
        """
        self.assertEqual(len(expected_assets), len(actual_assets))

        actual_assets_map = {asset['asset_key']: asset for asset in actual_assets}
        for expected_item in expected_assets:
            actual_item = actual_assets_map[expected_item['asset_key'].map_into_course(actual_course_key)]
            self.assertAssetEqual(expected_course_key, expected_item, actual_course_key, actual_item)

    def assertAssetsEqual(self, expected_store, expected_course_key, actual_store, actual_course_key):
        """
        Assert that the course assets identified by ``expected_course_key`` in ``expected_store`` and
        ``actual_course_key`` in ``actual_store`` are identical, allowing for differences related
        to their being from different course keys.
        """
        expected_content, expected_count = expected_store.get_all_content_for_course(expected_course_key)
        actual_content, actual_count = actual_store.get_all_content_for_course(actual_course_key)

        with self.bulk_assertions():

            self.assertEqual(expected_count, actual_count)
            self._assertAssetsEqual(expected_course_key, expected_content, actual_course_key, actual_content)

            expected_thumbs = expected_store.get_all_content_thumbnails_for_course(expected_course_key)
            actual_thumbs = actual_store.get_all_content_thumbnails_for_course(actual_course_key)

            self._assertAssetsEqual(expected_course_key, expected_thumbs, actual_course_key, actual_thumbs)

    def assertAssetsMetadataEqual(self, expected_modulestore, expected_course_key, actual_modulestore, actual_course_key):
        """
        Assert that the modulestore asset metdata for the ``expected_course_key`` and the ``actual_course_key``
        are equivalent.
        """
        expected_course_assets = expected_modulestore.get_all_asset_metadata(
            expected_course_key, None, sort=('displayname', ModuleStoreEnum.SortOrder.descending)
        )
        actual_course_assets = actual_modulestore.get_all_asset_metadata(
            actual_course_key, None, sort=('displayname', ModuleStoreEnum.SortOrder.descending)
        )
        self.assertEquals(len(expected_course_assets), len(actual_course_assets))
        for idx, __ in enumerate(expected_course_assets):
            for attr in AssetMetadata.ATTRS_ALLOWED_TO_UPDATE:
                if attr in ('edited_on',):
                    # edited_on is updated upon import.
                    continue
                self.assertEquals(getattr(expected_course_assets[idx], attr), getattr(actual_course_assets[idx], attr))
