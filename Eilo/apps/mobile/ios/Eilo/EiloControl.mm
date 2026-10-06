#import "EiloControl.h"
#import <React_RCTAppDelegate/RCTDefaultReactNativeFactoryDelegate.h>
#import "Eilo-Swift.h"
@implementation EiloControl {
  EiloControlHost *_host;
  NSTimer *_timer;
  NSString *_last;
  BOOL _invalidated;
}
RCT_EXPORT_MODULE(EiloControl)
+ (BOOL)requiresMainQueueSetup { return YES; }
- (instancetype)init {
  if (self = [super init]) {
    _host = [EiloControlHost new];
  }
  return self;
}
// React Native may construct an instance that never receives a JSI emitter.
// Creating a timer in init would invoke an empty generated std::function.
- (void)setEventEmitterCallback:(EventEmitterCallbackWrapper *)callback {
  @synchronized (self) {
    if (_invalidated) return;
    [super setEventEmitterCallback:callback];
  }
  dispatch_async(dispatch_get_main_queue(), ^{
    @synchronized (self) {
      if (self->_invalidated || self->_timer || !self->_eventEmitterCallback) return;
      __weak EiloControl *weakSelf = self;
      self->_timer = [NSTimer scheduledTimerWithTimeInterval:0.25 repeats:YES block:^(NSTimer *timer) {
        EiloControl *strongSelf = weakSelf;
        if (!strongSelf) { [timer invalidate]; return; }
        @synchronized (strongSelf) {
          if (strongSelf->_invalidated || !strongSelf->_eventEmitterCallback) {
            [timer invalidate]; return;
          }
          NSString *value = [strongSelf->_host snapshot];
          if (![value isEqualToString:strongSelf->_last]) {
            strongSelf->_last = value;
            [strongSelf emitOnSnapshot:value];
          }
        }
      }];
    }
  });
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
- (void)invalidate {
  @synchronized (self) {
    _invalidated = YES;
    _eventEmitterCallback = {};
  }
  dispatch_async(dispatch_get_main_queue(), ^{
    [self->_timer invalidate];
    self->_timer = nil;
  });
}
- (std::shared_ptr<facebook::react::TurboModule>)getTurboModule:(const facebook::react::ObjCTurboModule::InitParams &)params {
  return std::make_shared<facebook::react::NativeEiloControlSpecJSI>(params);
}
@end
