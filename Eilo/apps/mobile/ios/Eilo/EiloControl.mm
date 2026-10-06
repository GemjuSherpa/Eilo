#import "EiloControl.h"
#import <React_RCTAppDelegate/RCTDefaultReactNativeFactoryDelegate.h>
#import "Eilo-Swift.h"
@implementation EiloControl {
  EiloControlHost *_host;
  NSTimer *_timer;
  NSString *_last;
}
RCT_EXPORT_MODULE(EiloControl)
+ (BOOL)requiresMainQueueSetup { return YES; }
- (instancetype)init {
  if (self = [super init]) {
    _host = [EiloControlHost new];
    __weak EiloControl *weakSelf = self;
    _timer = [NSTimer scheduledTimerWithTimeInterval:0.25 repeats:YES block:^(NSTimer *timer) {
      EiloControl *strongSelf=weakSelf;
      if (!strongSelf) { [timer invalidate]; return; }
      NSString *value=[strongSelf->_host snapshot];
      if (![value isEqualToString:strongSelf->_last]) { strongSelf->_last=value;[strongSelf emitOnSnapshot:value]; }
    }];
  }
  return self;
}
- (void)getSnapshot:(RCTPromiseResolveBlock)resolve reject:(RCTPromiseRejectBlock)reject {
  dispatch_async(dispatch_get_main_queue(), ^{ resolve([self->_host snapshot]); });
}
- (void)command:(NSString *)name value:(NSString *)value resolve:(RCTPromiseResolveBlock)resolve reject:(RCTPromiseRejectBlock)reject {
  dispatch_async(dispatch_get_main_queue(), ^{
    if ([name isEqualToString:@"background"]) { [self->_host background:value completion:^(NSString *snapshot) { resolve(snapshot); }]; }
    else { resolve([self->_host command:name value:value]); }
  });
}
- (void)invalidate { [_timer invalidate];_timer=nil; }
- (std::shared_ptr<facebook::react::TurboModule>)getTurboModule:(const facebook::react::ObjCTurboModule::InitParams &)params {
  return std::make_shared<facebook::react::NativeEiloControlSpecJSI>(params);
}
@end
