"""
Standalone test for architecture gap fixes.

Tests the following improvements:
1. State helper functions
2. Validation helpers
3. Platform publish result creation
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from backend.utils.state_helpers import (
    create_success_update,
    create_error_update,
    create_platform_publish_result,
    merge_publish_results,
    validate_required_fields
)


def test_create_success_update():
    """Test create_success_update helper"""
    print("Test 1: create_success_update")
    print("-" * 40)

    result = create_success_update(
        agent_name="tiktok",
        data={"video_url": "https://example.com/video.mp4", "caption": "Test"}
    )

    assert result["current_agent"] == "tiktok"
    assert result["status"] == "success"
    assert result["video_url"] == "https://example.com/video.mp4"
    assert result["caption"] == "Test"

    print("PASS")
    print()


def test_create_error_update():
    """Test create_error_update helper"""
    print("Test 2: create_error_update")
    print("-" * 40)

    error = ValueError("Test error message")
    result = create_error_update(
        agent_name="youtube_shorts",
        error=error,
        context={"step": "upload"}
    )

    assert result["current_agent"] == "youtube_shorts"
    assert result["status"] == "failed"
    assert result["error_message"] == "Test error message"
    assert result["error_type"] == "ValueError"
    assert result["step"] == "upload"

    print("PASS")
    print()


def test_create_platform_publish_result():
    """Test create_platform_publish_result helper"""
    print("Test 3: create_platform_publish_result (success)")
    print("-" * 40)

    result = create_platform_publish_result(
        platform="tiktok",
        status="success",
        url="https://tiktok.com/@user/video/123",
        video_id="123",
        metadata={"caption": "Test caption", "hashtags": ["ai", "tech"]}
    )

    assert result["platform"] == "tiktok"
    assert result["status"] == "success"
    assert result["url"] == "https://tiktok.com/@user/video/123"
    assert result["video_id"] == "123"
    assert result["caption"] == "Test caption"
    assert result["hashtags"] == ["ai", "tech"]

    print("PASS")
    print()

    print("Test 4: create_platform_publish_result (failure)")
    print("-" * 40)

    result = create_platform_publish_result(
        platform="youtube_shorts",
        status="failed",
        error="Upload failed"
    )

    assert result["platform"] == "youtube_shorts"
    assert result["status"] == "failed"
    assert result["error"] == "Upload failed"
    assert "url" not in result

    print("PASS")
    print()


def test_merge_publish_results():
    """Test merge_publish_results helper"""
    print("Test 5: merge_publish_results")
    print("-" * 40)

    state = {
        "publish_results": {
            "tiktok": {"status": "success", "url": "https://tiktok.com/123"}
        }
    }

    new_result = {"status": "success", "url": "https://youtube.com/456"}

    update = merge_publish_results(state, "youtube_shorts", new_result)

    assert "publish_results" in update
    assert "tiktok" in update["publish_results"]
    assert "youtube_shorts" in update["publish_results"]
    assert update["publish_results"]["youtube_shorts"]["url"] == "https://youtube.com/456"

    print("PASS")
    print()


def test_validate_required_fields():
    """Test validate_required_fields helper"""
    print("Test 6: validate_required_fields (valid)")
    print("-" * 40)

    state = {
        "video_url": "https://example.com/video.mp4",
        "script": "Test script",
        "asset_pack": {}
    }

    error = validate_required_fields(
        state=state,
        required_fields=["video_url", "script", "asset_pack"],
        agent_name="tiktok"
    )

    assert error is None
    print("PASS")
    print()

    print("Test 7: validate_required_fields (missing)")
    print("-" * 40)

    state = {"video_url": "https://example.com/video.mp4"}

    error = validate_required_fields(
        state=state,
        required_fields=["video_url", "script", "asset_pack"],
        agent_name="tiktok"
    )

    assert error is not None
    assert error["current_agent"] == "tiktok"
    assert error["status"] == "failed"
    assert "script" in error["error_message"]
    assert "asset_pack" in error["error_message"]

    print("PASS")
    print()


def run_all_tests():
    """Run all tests"""
    print("=" * 80)
    print("GAP FIX VERIFICATION TESTS")
    print("=" * 80)
    print()

    try:
        test_create_success_update()
        test_create_error_update()
        test_create_platform_publish_result()
        test_merge_publish_results()
        test_validate_required_fields()

        print("=" * 80)
        print("ALL TESTS PASSED")
        print("=" * 80)
        return True

    except AssertionError as e:
        print()
        print("=" * 80)
        print(f"TEST FAILED: {e}")
        print("=" * 80)
        return False
    except Exception as e:
        print()
        print("=" * 80)
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
