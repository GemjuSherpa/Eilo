package com.eilo.foundation
import java.io.File
import java.net.Proxy
import java.net.URI
import java.util.concurrent.atomic.AtomicBoolean

class PackCancellation { private val flag=AtomicBoolean(false); fun cancel() { flag.set(true) }; fun check() { check(!flag.get()) { "cancelled" } } }
data class PackRequest(val url: String, val offset: Long, val etag: String?)
data class PackHeaders(val status: Int, val length: Long, val location: String?=null, val etag: String?=null, val range: String?=null, val encoding: String?=null)
interface PackHTTPClient { fun fetch(request: PackRequest, cancel: PackCancellation, response: (PackHeaders)->Unit, chunk: (ByteArray,Int)->Unit) }
/** Dedicated OkHttp client, isolated from React Native cookie/auth interceptors. */
class NativePackHTTPClient : PackHTTPClient {
 private val client=okhttp3.OkHttpClient.Builder().cookieJar(okhttp3.CookieJar.NO_COOKIES)
  .authenticator(okhttp3.Authenticator.NONE).proxyAuthenticator(okhttp3.Authenticator.NONE)
  .proxy(Proxy.NO_PROXY).followRedirects(false).followSslRedirects(false).cache(null)
  .retryOnConnectionFailure(false).connectionSpecs(listOf(okhttp3.ConnectionSpec.MODERN_TLS))
  .connectTimeout(15,java.util.concurrent.TimeUnit.SECONDS).readTimeout(15,java.util.concurrent.TimeUnit.SECONDS)
  .callTimeout(120,java.util.concurrent.TimeUnit.SECONDS).build()
 override fun fetch(request: PackRequest,cancel: PackCancellation,response: (PackHeaders)->Unit,chunk: (ByteArray,Int)->Unit) {
  cancel.check();val builder=okhttp3.Request.Builder().url(request.url)
   .header("Accept-Encoding","identity").header("User-Agent","Eilo-Model-Installer/1")
  if(request.offset>0) { builder.header("Range","bytes=${request.offset}-");builder.header("If-Range",request.etag!!) }
  val call=client.newCall(builder.build())
  try { call.execute().use { r ->
   response(PackHeaders(r.code,r.header("Content-Length")?.toLongOrNull() ?: -1,r.header("Location"),r.header("ETag"),r.header("Content-Range"),r.header("Content-Encoding")))
   if(r.code in 200..299) (r.body ?: error("transport")).byteStream().use { stream ->
    val buffer=ByteArray(65536);while(true) { cancel.check();val n=stream.read(buffer);if(n<0)break;chunk(buffer,n) }
   }
  } } finally { call.cancel() }
 }
}
class PackRestartRequired : Exception()
class PackOriginPolicy(origins: Set<String>) {
 private val origins=origins.toSet()
 fun allows(url: String): Boolean = try {
  val u=URI(url);val host=u.host ?: return false
  u.scheme=="https" && u.rawUserInfo==null && u.rawQuery==null && u.rawFragment==null && u.port in setOf(-1,443) && u.normalize()==u && !u.rawPath.contains('%') && !u.rawPath.contains('\\') &&
  host.matches(Regex("[a-z0-9.-]+")) && host!="localhost" && !host.matches(Regex("[0-9.]+")) && origins.contains("https://$host")
 } catch (_: Exception) { false }
}
/** Blocking disk/network work must be invoked on the dedicated installer worker, never UI/audio threads. */
class PackTransport(private val policy: PackOriginPolicy, private val client: PackHTTPClient=NativePackHTTPClient()) {
 fun transfer(pack: VerifiedPack,index: Int,file: File,cancel: PackCancellation,offset: Long=0,etag: String?=null,validator: (String?)->Unit={}): String? {
  val a=pack.manifest.artifacts[index];require(offset in 0 until a.bytes && (offset==0L || strongEtag(etag)))
  require(offset==0L || file.length()==offset)
  var url=a.url;var redirects=0
  while(true) {
   cancel.check();check(policy.allows(url)) { "origin" }
   var redirect: String?=null;var nextEtag: String?=null;var received=0L;var accepted=false
   var output: java.io.FileOutputStream?=null
   try {
    client.fetch(PackRequest(url,offset,if(offset>0)etag else null),cancel,{ h ->
     if(h.status in setOf(301,302,303,307,308)) { check(redirects<4 && h.location!=null);redirect=URI(url).resolve(h.location).toString() }
     else {
      if(offset>0 && (h.status!=206 || h.etag!=etag)) throw PackRestartRequired()
      check(h.status==(if(offset>0)206 else 200) && h.length==a.bytes-offset && (h.encoding==null || h.encoding=="identity")) { "transport" }
      if(offset>0) check(h.range=="bytes $offset-${a.bytes-1}/${a.bytes}") { "transport" }
      cancel.check();nextEtag=if(strongEtag(h.etag))h.etag else null;validator(nextEtag);check(!java.nio.file.Files.isSymbolicLink(file.toPath()));accepted=true;output=java.io.FileOutputStream(file,offset>0)
     }
    },{ bytes,n ->
     cancel.check();check(accepted && n in 0..bytes.size && n.toLong()<=a.bytes-offset-received) { "transport" };output!!.write(bytes,0,n);received+=n
    })
    if(redirect!=null) { url=redirect!!;redirects++;continue }
    check(accepted && received==a.bytes-offset) { "transport" };output!!.fd.sync();return nextEtag
   } finally { output?.close() }
  }
 }
 companion object { fun strongEtag(s: String?)=s!=null && s.matches(Regex("\"[a-zA-Z0-9._-]{1,128}\"")) }
}
