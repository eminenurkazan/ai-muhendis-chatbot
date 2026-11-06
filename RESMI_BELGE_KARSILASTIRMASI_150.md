# Son 150 kayıt için resmî belge karşılaştırması

150/150 kayıt karşılaştırıldı. Sonuç: {'partially_supported_scoped': 137, 'insufficient_support': 13}.
13 kayıtta resmî destek yetersiz: önceki açık kaynak-incelemesi aktarım onayı kapsamında tutulur, doğrulanmış olarak sunulmaz. Bütün cevap/kod veya ürün ortamı bağımsız test edilmedi.

## 1. serverfault:q944261:a944383 — partially_supported_scoped
UPN suffix ekleme/değiştirme domain rename işleminden ayrıdır. Belge UPN alternatifini destekler; kurumun domain rename ihtiyacının gereksiz olduğu hükmünü vermez.
- https://learn.microsoft.com/en-us/microsoft-365/enterprise/prepare-a-non-routable-domain-for-directory-synchronization

## 2. serverfault:q987348:a987373 — partially_supported_scoped
DHCP istemci Operational/Admin loglarını inceleme destekleniyor. 50028/50029'un tüm sürümlerde statik IP değişikliklerini eksiksiz izlediği onaylanmadı.
- https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/troubleshoot-problems-dhcp-client

## 3. serverfault:q1032233:a1035293 — partially_supported_scoped
DFSR staging kotası ve 4202/4204/4206/4208/4212 olayları tanı için kullanılabilir; her backlog aynı nedenden değildir.
- https://learn.microsoft.com/en-us/windows-server/troubleshoot/how-to-determine-the-minimum-staging-area-dfsr-needs-for-a-replicated-folder

## 4. serverfault:q1193445:a1193451 — partially_supported_scoped
Get-SmbConnection SMB istemcisinin sunucu bağlantılarını gösterir; bütün audit olaylarını veya kötü niyeti tek başına açıklamaz. Registry/reboot kısmı kapsam dışı.
- https://learn.microsoft.com/en-us/powershell/module/smbshare/get-smbconnection

## 5. serverfault:q972252:a972319 — partially_supported_scoped
AD FS Claims Provider Trust dış sağlayıcıdan token tüketme ilişkisini açıklar; her SSO ürünü/protokolüyle koşulsuz uyum yoktur. Özel STS örneği onaylanmadı.
- https://learn.microsoft.com/en-us/windows-server/identity/ad-fs/technical-reference/understanding-key-ad-fs-concepts

## 6. serverfault:q946277:a997160 — partially_supported_scoped
Eski Schannel trusted issuer list truncation vakası ve client sertifikası seçimi sorunu belgede yer alır. Registry sertifika deposu silme adımları indeks kapsamı dışında.
- https://learn.microsoft.com/en-us/troubleshoot/windows-server/windows-security/ssltls-communication-problems-after-install-kb931125

## 7. serverfault:q1163977:a1164013 — partially_supported_scoped
OpenSSH LogLevel ve servis günlüğü bağlantı teşhisinde kullanılabilir. Security 4625'in adres alanının her durumda dolu olacağı garantisi yok.
- https://learn.microsoft.com/da-dk/troubleshoot/windows-server/system-management-components/enable-openssh-verbose-logging

## 8. serverfault:q1090562:a1090564 — partially_supported_scoped
forestprep/schema master ile domainprep/infrastructure master ve gereken yetkiler ayrıdır. Kaynakta geçen /forest Dev seçeneği genel öneri yapılmadı.
- https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/adprep

## 9. serverfault:q931212:a931216 — insufficient_support
AWS Simple AD ile WorkDocs ilişkisi belgede var; GorillaBoyAdministrator adlı grubun işlevi/silinebilirliği doğrulanamadı. Yalnız topluluk yazarının Support aktarımıdır.
- https://docs.aws.amazon.com/directoryservice/latest/admin-guide/simple_ad_enable_apps_services.html

## 10. serverfault:q980476:a980479 — partially_supported_scoped
SPN sorgulama ve duplicate kontrolüyle -S kullanımı belgeli; alias hizmet hesabının sahibi ayrıca belirlenmeli, rastgele SPN eklenmemeli.
- https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/setspn

## 11. serverfault:q1041596:a1041717 — partially_supported_scoped
X-Robots-Tag noindex PDF gibi HTML dışı içerikte kullanılabilir; crawler erişimini engellemez ve bütün crawler'ları zorlamaz. Kaynak rewrite XML bütünü onaylanmadı.
- https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag

## 12. serverfault:q1017872:a1018534 — partially_supported_scoped
Security log forwarding için Network Service okuma yetkisi/Event Log Readers üyeliği belgeli. Kaynak SDDL dizgesi ve NS/SID farkı genel doğru kabul edilmedi.
- https://learn.microsoft.com/en-us/windows/win32/wec/setting-up-a-source-initiated-subscription

## 13. serverfault:q1165924:a1165929 — partially_supported_scoped
Cmdlet domain default password policy üzerinde Identity ile işlem yapar. Complexity kapatma domain güvenliğini etkiler; yalnız parametre/kimlik açıklaması korunur.
- https://learn.microsoft.com/en-us/powershell/module/activedirectory/set-addefaultdomainpasswordpolicy

## 14. serverfault:q1105003:a1105004 — partially_supported_scoped
Protected hesaplarda permission inheritance davranışı AdminSDHolder/SDProp ile açıklanır. Sorudaki hesabın gerçekten protected olduğu kanıtlanmadı; hipotezdir.
- https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/plan/security-best-practices/appendix-c--protected-accounts-and-groups-in-active-directory

## 15. serverfault:q983783:a983808 — partially_supported_scoped
forwarded ayarı mesajın kaynakta render edildiğini varsayan Winlogbeat okumasını etkiler. XML EventData ile rendered message farklıdır.
- https://www.elastic.co/docs/reference/beats/winlogbeat/configuration-winlogbeat-options

## 16. serverfault:q900508:a900512 — partially_supported_scoped
DirectorySearcher search root/filter ile dizin sorgular; RSAT cmdlet'i şart değildir. Dizin erişimi ve arama yetkisi yine gereklidir.
- https://learn.microsoft.com/en-us/dotnet/api/system.directoryservices.directorysearcher?view=netframework-4.8

## 17. serverfault:q962417:a962817 — partially_supported_scoped
Modern CAPI2 kanalı enable/channel access ayarları klasik CustomSD yolundan ayrılır; GPO/wevtutil yöntemi belgeli. Görseldeki tam ACL üretilmedi.
- https://learn.microsoft.com/windows/security/operating-system-security/device-management/use-windows-event-forwarding-to-assist-in-intrusion-detection

## 18. serverfault:q1060794:a1060921 — insufficient_support
Belge yalnız sürümce desteklenen Schannel ayarlarının kullanılmasını önerir. TLS 1.3 anahtarını silmenin sorudaki HTTPS sorununu çözdüğü bağımsız/resmî olarak doğrulanamadı; doğrudan öneri kaldırılmalı.
- https://learn.microsoft.com/windows-server/security/tls/tls-registry-settings

## 19. serverfault:q956312:a956545 — partially_supported_scoped
Shell replacement kullanıcı arayüzünü değiştirir; diğer programlara erişimi kendi başına engellemez. Güvenli kiosk garantisi değildir.
- https://learn.microsoft.com/en-us/windows/configuration/shell-launcher/

## 20. serverfault:q972740:a991764 — partially_supported_scoped
HTTP error log alanları ErrorLoggingFields ile seçilebilir; kaynak bitmask toplamı ve streamid sürüm tablosu onaylanmadı.
- https://learn.microsoft.com/en-us/windows/win32/http/error-logging-in-windows-server-2003-sp1

## 21. serverfault:q1003010:a1003014 — partially_supported_scoped
Install-WindowsFeature yerel/uzak Windows Server rolleri/özelliklerini veya offline VHD'yi hedefleyebilir. Yalnız canlı OS'ye uygulanır şeklindeki eski özet daraltıldı.
- https://learn.microsoft.com/en-us/powershell/module/servermanager/install-windowsfeature

## 22. serverfault:q1025390:a1025399 — partially_supported_scoped
HTTPS binding için doğru sertifika hash/store seçimi kontrol edilebilir; bütün authentication prompt sorunlarının nedeni sertifika değildir.
- https://learn.microsoft.com/en-gb/iis/manage/configuring-security/how-to-set-up-ssl-on-iis

## 23. serverfault:q1068507:a1156475 — partially_supported_scoped
IE ESC ZoneMap ESCDomains geçmiş Windows sürümlerinde belgeli. Her MMC/about:security_mmc sorunu için aynı registry değişikliği garantilenmez.
- https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/intranet-site-identified-as-an-internet-site

## 24. serverfault:q1030998:a1031001 — partially_supported_scoped
Chrome 58 CN fallback'i kaldırmıştır; hedef DNS adının SAN'da yer alması önemlidir. Bütün istemciler için eski IIS CN anlatımı yeterli değil.
- https://developer.chrome.com/blog/chrome-58-deprecations

## 25. serverfault:q946779:a946789 — partially_supported_scoped
SCOM event data saklama/grooming ayarlarına sahiptir. SCOM hiç log toplamaz veya full-text çözümü yerine her zaman kullanılamaz hükmü verilmez; kapasite ihtiyacı ayrı değerlendirilir.
- https://learn.microsoft.com/en-us/system-center/scom/manage-omdb-grooming-settings

## 26. serverfault:q1138424:a1138425 — partially_supported_scoped
Mesaj kaynak dosyalarının event source ile kaydı render için önemlidir. Eski Event Logging API kaydı ile modern manifest API ayrılmalı; PATH değişikliği genel çözüm değildir.
- https://learn.microsoft.com/en-us/windows/win32/eventlog/message-files

## 27. serverfault:q1188120:a1188130 — partially_supported_scoped
1644 pahalı/yavaş LDAP aramalarını teşhis eder. Eşik/log artışı hassas sorguları ve yüksek hacmi açığa çıkarabilir; her LDAPS paketini çözmez.
- https://learn.microsoft.com/en-us/troubleshoot/windows-server/active-directory/event1644reader-analyze-ldap-query-performance

## 28. serverfault:q906706:a906782 — partially_supported_scoped
Event XML ve EventData alanları olayın şemasına göre sorgulanmalıdır; bütün ID'lerde property dizisinin aynı sıra olduğu varsayılamaz.
- https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent?view=powershell-5.1

## 29. serverfault:q955112:a955113 — partially_supported_scoped
Zone apex/root kaydı host adından ayrılır; @ zone kökünü temsil eder. UI'de parent folder ifadesi dosya sistemi dizini değildir.
- https://learn.microsoft.com/en-us/powershell/module/dnsserver/add-dnsserverresourcerecorda

## 30. serverfault:q1043773:a1043778 — partially_supported_scoped
Get-WebConfiguration filtre/path/location ile etkin yapılandırmayı sorgular; okumayla değiştirme/silme işlemleri ayrıdır.
- https://learn.microsoft.com/en-us/powershell/module/webadministration/get-webconfiguration

## 31. serverfault:q897253:a897262 — partially_supported_scoped
pwdLastSet parola son değişim zamanını tutar; 0 uygun bayrak koşulunda sonraki girişte değişim ister. Hesap expires ile aynı değildir; toplu reset reçetesi onaylanmadı.
- https://learn.microsoft.com/en-us/windows/win32/adschema/a-pwdlastset

## 32. serverfault:q1119734:a1119737 — partially_supported_scoped
get_current_user PHP script sahibini döndürür; web isteğini yapan kullanıcı değildir. AUTH_USER sunucu tarafından doğrulanmış kimlik bağlamında değerlendirilmelidir.
- https://www.php.net/manual/en/function.get-current-user.php

## 33. serverfault:q899375:a899406 — partially_supported_scoped
Runas/ShellRunas farklı kimlikle program başlatır; netonly yalnız uzak erişim credential'ını etkiler. Event Viewer uzak log yetkisi ve bağlantı şartları ayrıca gerekir.
- https://learn.microsoft.com/en-us/sysinternals/downloads/shellrunas

## 34. serverfault:q1141526:a1141527 — partially_supported_scoped
2016 Essentials için belgelenmiş maksimum RAM 64 GB. Sonraki Essentials sürümlerine aynı sınır genellenmemeli.
- https://learn.microsoft.com/en-us/previous-versions/windows-server/it-pro/windows-server-essentials/install/Hardware-Requirements-for-the-Target-Computer

## 35. serverfault:q901692:a904638 — partially_supported_scoped
Java 8u251 notları RSASSA-PSS desteği eklenmesini listeler; bütün Java 8 sürümlerinde destek yok iddiası yanlıştır. Yalnız eski ortamda raporlanmış algoritma uyumu vakası korunur.
- https://www.oracle.com/java/technologies/javase/8u251-relnotes.html

## 36. serverfault:q895161:a895168 — partially_supported_scoped
Cipher suite aileleri authentication algoritmasına ve OS sürümüne bağlıdır. Sunucu sertifikası ve etkin suite uyumunu kontrol etme desteklenir; yalnız GCM açınca tüm istemcilerde çalışır garantisi yoktur.
- https://learn.microsoft.com/en-us/windows/win32/secauthn/tls-cipher-suites-in-windows-8

## 37. serverfault:q973823:a973857 — partially_supported_scoped
Logon, credential validation ve Kerberos olayları farklı audit subcategory ve makinelerde oluşabilir. Tek Event Viewer logunda bütün authentication hatalarının bulunması beklenmez.
- https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/plan/security-best-practices/advanced-audit-policy-configuration

## 38. serverfault:q922707:a922708 — partially_supported_scoped
LDAPFilter/Filter ve Properties ile dizin attribute'ları sorgulanabilir. Kaynakta verilen tam proxyAddresses filtre eşleşmesi ayrıca gerçek veriyle kontrol edilmeli; prefix/pattern genellenmemeli.
- https://learn.microsoft.com/en-us/powershell/module/activedirectory/get-adobject?view=windowsserver2025-ps

## 39. serverfault:q1049420:a1049426 — partially_supported_scoped
Source-initiated ve domain dışı subscription için collector/subscription ile sertifika/WinRM önkoşulları belgeli; sadece wecutil listelemek subscription yaratmaz.
- https://learn.microsoft.com/en-us/windows/win32/wec/setting-up-a-source-initiated-subscription

## 40. serverfault:q1010266:a1010301 — partially_supported_scoped
Get-SmbSession server tarafı oturumlarda Dialect alanını gösterir. İstemci Get-SmbConnection ile aynı kapsam değildir.
- https://learn.microsoft.com/en-us/powershell/module/smbshare/get-smbsession?view=windowsserver2025-ps

## 41. serverfault:q925304:a925306 — partially_supported_scoped
FGPP kullanıcılar/global security gruplarına uygulanır; OU'ya doğrudan PSO ataması değildir. Precedence ve domain önkoşulları kontrol edilmelidir.
- https://learn.microsoft.com/windows-server/identity/ad-ds/get-started/adac/fine-grained-password-policies

## 42. serverfault:q1103419:a1103531 — partially_supported_scoped
4660 gerçek delete olayını ve handle bilgisini, 4663 object/access bilgisini verebilir. SACL/audit şartları olmadan eksiksiz kayıt garantisi yoktur; 4663 rename gibi başka eylemlerde de çıkabilir.
- https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4660

## 43. serverfault:q927114:a927407 — partially_supported_scoped
RDS listener Win32_TSGeneralSetting.SSLCertificateSHA1Hash kullanır; sertifikanın computer Personal store'da bulunması ve private-key erişimi önemlidir. Bütün RDS rolleri için tek binding değildir.
- https://learn.microsoft.com/en-us/troubleshoot/windows-server/remote/remote-desktop-listener-certificate-configurations

## 44. serverfault:q939580:a939608 — partially_supported_scoped
Require SSL ve client certificate Ignore/Accept/Require ayrı ayarlardır. Tüm 403 hatalarının aynı sebebe sahip olduğu sonucu çıkarılmaz.
- https://learn.microsoft.com/en-us/iis/application-frameworks/scenario-build-an-aspnet-website-on-iis/configuring-step-4-configure-application-security

## 45. serverfault:q955721:a955723 — partially_supported_scoped
Primary group RID'si primaryGroupID ile temsil edilir; memberOf backlink listesini tüm grup üyeliklerinin eksiksiz listesi saymak doğru değildir.
- https://learn.microsoft.com/en-us/windows/win32/adschema/a-primarygroupid

## 46. serverfault:q949589:a949599 — insufficient_support
Integrated Security domain trust/DNS/SPN yerine geçmez. Ancak kaynak cevabındaki bütün non-trusted domain düzenleri için koşulsuz hayır hükmü doğrulanmadı; hesap/protokol/topoloji belirsiz.
- https://learn.microsoft.com/en-us/sql/connect/ado-net/sql/authentication-sql-server

## 47. serverfault:q1132723:a1132724 — insufficient_support
HPE AMS için kaynak yazarının polling/NetSetupSvc korelasyonunu doğrulayan erişilebilir ürün belgesi bulunamadı. Decompile/undocumented registry ayarları desteklenmiş sayılmaz; tarihsel kullanıcı raporu olarak kalır.

## 48. serverfault:q974537:a974541 — partially_supported_scoped
ADAC/Unlock-ADAccount için eski sürüm issue/hotfix ve account restriction workaround'u resmî kayıtta var. Bu haklar fazladan güvenlik etkisi doğurabilir; yeni bütün sürümlere genellenmez.
- https://support.microsoft.com/en-au/topic/unlocking-a-user-account-fails-when-using-adac-or-the-unlock-adaccount-cmdlet-in-windows-7-or-windows-server-2008-r2-even-if-sufficient-permissions-are-granted-ac15ff8a-a485-3560-3ed8-12f40778b8e3

## 49. serverfault:q1123692:a1123757 — partially_supported_scoped
4776 NTLM credential validation olayıdır ve Source Workstation/account/error code verir; 4625 Subject/Target şemasıyla aynı değildir. Önceki genel Subject özeti bu farkla daraltılır.
- https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4776

## 50. serverfault:q1020562:a1020621 — partially_supported_scoped
maxAllowedContentLength bytes cinsindedir ve effective requestFiltering konfigürasyonuna bağlıdır. ARR giriş katmanındaki limit ayrı olabilir; bütün limitleri sınırsız artırma önerilmez.
- https://learn.microsoft.com/en-us/troubleshoot/developer/webapps/iis/site-behavior-performance/http-404-13-website

## 51. serverfault:q1118552:a1118572 — partially_supported_scoped
TCP FIN bağlantı yönünün kapanışını gösterir. İki uçtaki trace sırası kapatan tarafı araştırmada kullanılabilir; uygulamanın neden kapattığını tek başına kanıtlamaz.
- https://www.rfc-editor.org/rfc/rfc9293.html

## 52. serverfault:q911131:a911230 — partially_supported_scoped
secedit /export user_rights/securitypolicy alanlarını dışa aktarabilir. User rights assignment'ı her zaman sıradan registry policy key'i saymak yanlıştır.
- https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/secedit-export

## 53. serverfault:q1034834:a1034954 — partially_supported_scoped
TLS sonlandıran proxy arkasında doğru scheme/forwarded headers önemlidir; yanlış scheme HTTPS redirect döngüsüne yol açabilir. Güvenilen proxy listesi ve middleware sırası sürüme göre gerekir.
- https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/proxy-load-balancer?view=aspnetcore-6.0

## 54. serverfault:q1048699:a1048734 — partially_supported_scoped
RDP bağlantı ve shutdown başlatma olayları izlenebilir; timestamp/kullanıcı oturumu korelasyonu teşhis yaklaşımıdır. Her shutdown'u kesin bir uzak IP'ye bağlama garantisi yoktur.
- https://learn.microsoft.com/windows/security/operating-system-security/device-management/use-windows-event-forwarding-to-assist-in-intrusion-detection

## 55. serverfault:q1043774:a1043777 — partially_supported_scoped
defaultDocument IIS configuration özelliğidir; site ayarını kapatmak OS rol özelliğini kaldırmakla aynı işlem değildir. OS feature removal alternatifinden vazgeçildi.
- https://learn.microsoft.com/en-us/iis/web-hosting/web-server-for-shared-hosting/default-documents

## 56. serverfault:q1041421:a1041434 — partially_supported_scoped
5136 Directory Service Changes ve uygun object/attribute SACL gerektirir; değişen attribute ve object ile filtrelenebilir. Her mail değişiminde default olarak olay oluşmaz.
- https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-5136

## 57. serverfault:q895638:a897379 — partially_supported_scoped
Server release/build ve WSL kurulum desteği birlikte kontrol edilir; mevcut belge 2019/1709+ ve sonrası yolları ayırır. 2016 build 14393'te feature adı varmış gibi zorlanmamalı; AWS AMI bulunabilirliği doğrulanmadı.
- https://learn.microsoft.com/en-us/windows/wsl/install-on-server

## 58. serverfault:q1140171:a1140186 — partially_supported_scoped
Zone root/apex için host etiketinden ayrı kayıt kullanılır. GUI boş isim ve -Name @ örneklerinin sürüm/komut parametresi ayrıca kontrol edilmelidir; bu ayrıntı onay kapsamı dışında.
- https://learn.microsoft.com/en-us/powershell/module/dnsserver/add-dnsserverresourcerecord?view=windowsserver2025-ps

## 59. serverfault:q1158673:a1158678 — partially_supported_scoped
Deny log on locally yerel etkileşimli oturum hakkını etkiler; RDP/network logon hakları ve IIS Windows Authentication ayrı kapsamdır. Bütün erişimi engelleme garantisi yoktur.
- https://learn.microsoft.com/en-us/windows/security/threat-protection/security-policy-settings/deny-log-on-locally

## 60. serverfault:q962477:a966450 — partially_supported_scoped
Bu policy logon olmadan shutdown erişimini etkiler. Kaynaktaki unexpected shutdown nedenini kanıtlamaz; tüm shutdown sorunları için çözüm sayılmaz.
- https://learn.microsoft.com/ja-jp/previous-versions/windows/it-pro/windows-10/security/threat-protection/security-policy-settings/shutdown-allow-system-to-be-shut-down-without-having-to-log-on

## 61. serverfault:q1193454:a1193455 — partially_supported_scoped
CRL yayınlama hedefi ile relying party'nin CDP erişim adresi farklı olabilir. HTTP/LDAP dağıtımı ve CA publication path ayrı değerlendirilir; UNC bütün istemcilerde yasaktır iddiası onaylanmadı.
- https://learn.microsoft.com/en-us/windows-server/identity/ad-cs/operate-certificate-revocation-crl-cdp

## 62. serverfault:q906138:a906179 — partially_supported_scoped
IIS process identity/ACL ilişkisi belgeli; app pool'a özgü ACL ile bütün IIS_IUSRS grubuna izin vermek farklı izolasyon sağlar. Kaynakta yapılan genişletme güvenli genel çözüm değildir.
- https://learn.microsoft.com/en-us/troubleshoot/developer/webapps/iis/was-service-svchost-process-operation/understanding-identities

## 63. serverfault:q927607:a927629 — partially_supported_scoped
AD FS certificate sharing container service account/private key paylaşımıyla ilişkilidir. Service account değişikliği sonrası erişim kontrolü makul hipotezdir; Event329 kök nedeni bu vakada kanıtlanmadı.
- https://learn.microsoft.com/en-us/powershell/module/adfs/set-adfscertsharingcontainer?view=windowsserver2025-ps

## 64. serverfault:q922693:a926534 — partially_supported_scoped
SNI hostname'i TLS handshake'e taşır; geleneksel ve SNI binding'ler birlikteyken gerçek binding'ler kontrol edilmeli. Kaynak görselindeki tam sertifika/IP ayarı tamamlanamaz.
- https://learn.microsoft.com/en-us/iis/get-started/whats-new-in-iis-8/iis-80-server-name-indication-sni-ssl-scalability

## 65. serverfault:q900372:a900421 — partially_supported_scoped
Script block logging etkinleştirildiğinde Operational 4104 üretilebilir; PowerShell 5.1 ve PowerShellCore log/provider adları ayrılır. Her URL isteğinin bütün içeriği varsayılan kaydedilir iddiası yok.
- https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_logging_windows

## 66. serverfault:q922725:a923202 — partially_supported_scoped
ARR+URL Rewrite reverse proxy mimarisini destekler; kimlik doğrulama ve backend ağ izolasyonu ayrıca tasarlanır. Kaynak Apache NTLM Basic fallback kodu onaylanmadı.
- https://learn.microsoft.com/en-us/iis/extensions/url-rewrite-module/reverse-proxy-with-url-rewrite-v2-and-application-request-routing

## 67. serverfault:q896646:a896650 — partially_supported_scoped
SPN benzersizliği ve doğru servis hesabında bulunması domain auth için önemlidir. Kaynaktaki BORON/SNOWDROP isimlerine göre otomatik silme talimatı çıkarılmaz.
- https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/setspn

## 68. serverfault:q1026925:a1027021 — partially_supported_scoped
Event channel'lar ayrı akışlardır; collector/view onları bir arada göstermeye yarar. Custom View kaynak olayın başka loga fiziksel kopyalandığını göstermez.
- https://learn.microsoft.com/en-us/windows/win32/wec/windows-event-collector

## 69. serverfault:q1046449:a1046452 — partially_supported_scoped
DC OS uyumluluğu hedef domain/forest level tablosundan kontrol edilir. Yükseltmeden önce forest/replication sağlığı gerekir; koşulsuz without issue garantisi yok.
- https://learn.microsoft.com/nb-no/windows-server/identity/ad-ds/active-directory-functional-levels

## 70. serverfault:q939367:a939370 — partially_supported_scoped
UNC erişim yolu server ve share bileşenlerine dayanır; yalnız server köküyle belirli bir paylaşım klasörü aynı hedef değildir.
- https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file

## 71. serverfault:q1026564:a1026570 — partially_supported_scoped
4648 explicit credentials kullanılarak logon denemesini gösterir; Subject, kullanılan credential ve Target ayrı alanlardır. Sırf isim farkı kötü niyet veya başarılı oturum kanıtı değildir.
- https://learn.microsoft.com/ja-jp/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4648

## 72. serverfault:q1058639:a1058662 — partially_supported_scoped
DNS owner adı zone root'a ait olabilir; same as parent folder ifadesi zone köküyle ilgilidir. Dosya sistemi dizini anlamına gelmez.
- https://learn.microsoft.com/en-us/powershell/module/dnsserver/add-dnsserverresourcerecord?view=windowsserver2025-ps

## 73. serverfault:q1015565:a1015572 — partially_supported_scoped
PUBLIC/PublicDesktop known folder kavramları belgeli; sabit C yolu yerine değişken/known folder değerlendirilir. Her GPP bağlamında aynı genişletme ve redirect sonucu garanti edilmez.
- https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid

## 74. serverfault:q1097752:a1097767 — partially_supported_scoped
community.windows.win_eventlog_entry belirli loga kayıt yazabilir; community collection sürümü ve source/log yetkileri gerekir. Her Ansible eylemi otomatik eventlog kaydı üretmez.
- https://docs.ansible.com/projects/ansible/latest/collections/community/windows/win_eventlog_entry_module.html

## 75. serverfault:q970404:a970429 — insufficient_support
Resmî ARR/rewrite belgesi reverse proxy düzenini destekler; kaynak sorudaki vanity route hatasının bütün uygulamaları aynı app pool'a alarak çözüleceği sonucu doğrulanmadı. Aynı pool genellemesi kaldırılmalı.
- https://learn.microsoft.com/en-us/iis/extensions/url-rewrite-module/reverse-proxy-with-url-rewrite-v2-and-application-request-routing

## 76. serverfault:q980215:a980787 — partially_supported_scoped
CurrentCulture thread/runtime/user ayarlarına bağlıdır; IIS identity context farklılığı araştırılabilir. Başka kullanıcının registry ayarlarını kopyalama desteklenen genel prosedür değildir.
- https://learn.microsoft.com/en-us/dotnet/api/system.globalization.cultureinfo.currentculture

## 77. serverfault:q989203:a991125 — insufficient_support
FSRM file screening işlevi belgeli; kaynakta bildirilen Server2019 junction bug'ı ve reboot zorunluluğu bu belgede doğrulanmıyor. Tarihsel yazar raporudur; screens kaldırma genel çözüm değildir.
- https://learn.microsoft.com/en-us/windows-server/storage/fsrm/file-screening-management

## 78. serverfault:q994930:a994933 — partially_supported_scoped
Edge proxy ve backend ayrı TLS sonlandırma noktaları olarak tasarlanabilir. Kaynaktaki IIS sürümü/binding TLS desteği için kesin tablo onaylanmadı.
- https://learn.microsoft.com/en-us/iis/extensions/url-rewrite-module/reverse-proxy-with-url-rewrite-v2-and-application-request-routing

## 79. serverfault:q961757:a961769 — partially_supported_scoped
OpenSSH sshd_config/service/ACL yapılandırması yönetilir; ürün/sürüm ve servis/firewall dağıtımı ayrıca kontrol edilir. Server2016'ya yerleşik GPO var/yok konusunda mutlak hüküm verilmedi.
- https://learn.microsoft.com/en-us/windows-server/administration/OpenSSH/openssh-server-configuration

## 80. serverfault:q952407:a952418 — partially_supported_scoped
Forwarded/rendered mesaj ile structured event alanları ayrılır. Message'ı her durumda bilgi kaybetmeden atma hükmü yok; message resource/localization gerekleri değerlendirilir.
- https://www.elastic.co/docs/reference/beats/winlogbeat/configuration-winlogbeat-options

## 81. serverfault:q913015:a913220 — partially_supported_scoped
WEF seçilen olayları source üzerinde okur ve subscription query ile collector'a yollar. Kaynak filtre/subscription tipi kontrol edilmeden tüm eventlerin önce collector'a gittiği varsayılamaz.
- https://learn.microsoft.com/windows/security/operating-system-security/device-management/use-windows-event-forwarding-to-assist-in-intrusion-detection

## 82. serverfault:q1143280:a1143281 — partially_supported_scoped
allowUnlisted default kararını ve sırayla işlenen allow/deny kurallarını ayırmak gerekir; default deny ancak gerekli allow ve doğru istemci IP'siyle kullanılmalıdır.
- https://learn.microsoft.com/en-us/iis/configuration/system.webserver/security/ipsecurity/

## 83. serverfault:q934165:a934224 — insufficient_support
KB3080079 için erişilebilir tam Microsoft sürüm/önkoşul kaydı bu araştırmada doğrulanamadı. Kaynaktaki Windows7/RDP güncelleme ilişkisi tarihsel rapor olarak kalır; kurulumu genel çözüm sayılmaz.

## 84. serverfault:q908341:a909752 — partially_supported_scoped
Process Monitor registry/file/process etkinliğini gözleyebilir. HIPS loguyla zaman korelasyonu tanı yöntemidir; McAfee için güvenli exception değeri veya bütün HIPS'i kapatma desteklenmedi.
- https://learn.microsoft.com/en-us/sysinternals/downloads/procmon

## 85. serverfault:q1022432:a1022443 — partially_supported_scoped
Windows ChrootDirectory desteği v7.7.0.0 ve SFTP ile sınırlıdır; ForceCommand internal-sftp açıklanır. SSH shell veya eksik ownership/ACL ile tam izolasyon garantilenmez.
- https://learn.microsoft.com/en-us/windows-server/administration/OpenSSH/openssh-server-configuration

## 86. serverfault:q948454:a948665 — partially_supported_scoped
Update source'a bağlantı/firewall/proxy kontrolü tanı içindir. Kaynakta firewall açınca çözüldüğü, bütün 0% download vakaları için doğrulanmış neden değildir.
- https://learn.microsoft.com/en-us/troubleshoot/windows-client/deployment/common-windows-update-errors

## 87. serverfault:q930424:a941348 — partially_supported_scoped
Sistem yönetimli pagefile boyutu commit ve crash dump gereğine bağlıdır. Belgede Windows10/11 tablosu vardır; tüm Server2016/Exchange iş yüklerine aynı formül dayatılmadı.
- https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/how-to-determine-the-appropriate-page-file-size-for-64-bit-versions-of-windows

## 88. serverfault:q913236:a913315 — partially_supported_scoped
LoadBalanceInfo protokolde yönlendirmeyle ilişkili opaque veridir; istemcinin rastgele düzenleyeceği serbest metin sayılmaz. RDWeb/Broker tarafından üretilen RDP tercih edilir.
- https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/df3d59e6-30a8-4a36-bd2d-9d11bcd96c3e

## 89. serverfault:q1031988:a1032018 — partially_supported_scoped
ADS, metadata ve erişilemeyen dosyalar görünür dosya toplamıyla volume kullanılan alanı arasında fark yaratabilir. Belirli üçüncü taraf scanner'ın bütün nedenleri eksiksiz saydığı garanti edilmez.
- https://learn.microsoft.com/cs-cz/troubleshoot/windows-server/backup-and-storage/disk-space-problems-on-ntfs-volumes

## 90. dba:q252954:a253002 — partially_supported_scoped
RMAN cmdfile substitution değişkenleri desteklenir; shell tarih üretimi RMAN'in kendi tarih fonksiyonu değildir. TAG uzunluğu/sözdizimi ayrıca sürüme göre kontrol edilmeli.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/rcmrf/RMAN.html

## 91. dba:q204314:a204325 — partially_supported_scoped
Constraint state ve QUERY_REWRITE_INTEGRITY join elimination davranışını etkileyebilir. Sırf FK var diye her sorguda join kaldırılır veya performans artar garantisi yok.
- https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/QUERY_REWRITE_INTEGRITY.html

## 92. dba:q214067:a214117 — partially_supported_scoped
DATE arithmetic ile tarih farkı hesaplanabilir; string dönüşümleri ve SQL/PLSQL çağrı maliyeti performans hipotezidir. Kaynak bitmap index/konkürens tarifi ve DATE fiziksel sayı olarak saklanır genellemesi onaylanmadı.
- https://docs.oracle.com/cd/A91202_01/901_doc/server.901/a90125/sql_elements2.htm

## 93. dba:q299932:a299950 — partially_supported_scoped
Analytic PARTITION BY sonucu gruplara ayırır; SUM OVER satırları GROUP BY gibi tek satıra indirmez. İki sorgunun performansı gerçek plan/istatistikle karşılaştırılmalıdır.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Analytic-Functions.html

## 94. dba:q333333:a333343 — insufficient_support
Dokümante view tablo alanının durumunu verir; SYS.TS$.ONLINE$ dahili kod 3 yorumunun desteklenen API anlamı olduğu doğrulanmadı. Dahili metadata doğrudan değiştirilmemeli.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/DBA_TABLESPACES.html

## 95. dba:q315247:a315248 — partially_supported_scoped
TDE ile RMAN backup encryption farklı katmanlardır; fiziksel yedekleme uygulama kolonunun açık metin dışa aktarımı değildir. Wallet/key ve hedef encryption şartları ayrıca gerekir.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/asoag/general-considerations-of-using-transparent-data-encryption.html

## 96. dba:q302522:a302604 — partially_supported_scoped
QB_NAME query block'a ad verir ve hedefli hint için kullanılabilir; tek başına query block'a ad vermek garantili hızlanma değildir.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Comments.html

## 97. dba:q233469:a233470 — partially_supported_scoped
MOVE veriyi yeni segmente taşır; destination alanı ve index/online move koşulları ayrıca değerlendirilir. Kaynaktaki yaklaşık alan hesabı her segment için kesin sayı değildir.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/ALTER-TABLE.html

## 98. dba:q239966:a239967 — partially_supported_scoped
ALTER SEQUENCE/RESTART davranışı sürüme bağlıdır. Sequence LAST_NUMBER cache metadata'sı ile gerçek son tablo ID'si/satır sayısı aynı değildir; concurrent reseed prosedürü onaylanmadı.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/admin/managing-views-sequences-and-synonyms.html

## 99. dba:q206993:a207001 — partially_supported_scoped
ORA-01537 dosyanın zaten veritabanına ait olduğu durumdur; farklı dosya adı gerekebilir. Mevcut dosyayı silme/üzerine yazma veya tablespace adıyla dosya adı eşitliği sonucu çıkarılmaz.
- https://docs.oracle.com/en/error-help/db/ora-01537/

## 100. dba:q269856:a269861 — partially_supported_scoped
Data Pump server-side directory object ve dosya erişimi kullanır; uzak SQLPlus istemcisinin yerel klasörüne kendiliğinden export olmaz. OS transferi ayrı işlem.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sutil/oracle-data-pump-overview.html

## 101. dba:q247247:a247297 — partially_supported_scoped
LOB ailesi BLOB/CLOB/NCLOB/BFILE içerir; BFILE harici dosya referansı ile iç LOB aynı değildir. Tek bir değişmez maksimum boyut bütün sürümlere genellenmez.
- https://docs.oracle.com/cd/B28359_01/appdev.111/b28393.pdf

## 102. dba:q333227:a333246 — partially_supported_scoped
SET NEWNAME sonrası RESTORE ve SWITCH dosya eşlemesi açıkça belgeli. DB_FILE_NAME_CONVERT/LOG_FILE_NAME_CONVERT'in her standalone restore'da yeterli olduğu iddiası onaylanmadı.
- https://docs.oracle.com/en/database/oracle/oracle-database/21/rcmrf/RESTORE.html

## 103. dba:q230488:a230497 — partially_supported_scoped
Foreign key child-parent referential integrity tanımlar. Basit one-to-many için ayrı link table zorunlu değildir; geçmiş/relationship attribute ve cardinality ihtiyacı şema kararıdır, tek doğru tasarım yok.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/constraint.html

## 104. dba:q282935:a282971 — partially_supported_scoped
PARALLEL statement/object hedefi ve degree anlamı syntax'a bağlıdır. Hint seçimi plan/edition/resource koşullarıyla değerlendirilir; daha yüksek DOP garanti hız değildir.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Comments.html

## 105. dba:q341477:a341485 — partially_supported_scoped
AUTOEXTENSIBLE ve MAXSIZE ayrıca incelenmelidir; yüksek doluluk yüzdesi tek başına büyüyemiyor anlamına gelmez. Audit her durumda SYSAUX'tadır ve DB kesin donar iddiası dışarıda.
- https://docs.oracle.com/html/E25494_01/dfiles003.htm

## 106. dba:q340526:a340528 — partially_supported_scoped
SET UNTIL hedefi RESTORE ve RECOVER için birlikte belirlenir; incomplete recovery sonrası RESETLOGS koşulludur. Örnek tarih/komutlar bütün restore için hazır prosedür değildir.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/rcmrf/RECOVER.html

## 107. dba:q316571:a316574 — partially_supported_scoped
Full transportable yöntem kullanıcı tabloları/metadata aktarımını genişletebilir; sürüm/platform/object sınırlamaları ve ayrı metadata export ihtiyacı kontrol edilir. Her PL/SQL nesnesi yalnız datafile taşımayla gelmez.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sutil/oracle-data-pump-overview.html

## 108. dba:q227069:a227507 — partially_supported_scoped
Partitioned outer join partition bazında outer join ile data densification sağlar; analitik partition ile aynı işlem değildir. Cross product emülasyonunun her NULL/duplicate durumda birebir eşdeğerliği onaylanmadı.
- https://docs.oracle.com/database/121/SQLRF/E41329-25.pdf

## 109. dba:q245779:a245971 — partially_supported_scoped
System.Data.OracleClient deprecated olarak belgelenmiştir. Kaynak SSIS aktarımında provider değişikliğinin faydasını kendi ortamında bildirir; eski provider güncel tavsiye veya evrensel hızlanma değildir.
- https://learn.microsoft.com/en-us/dotnet/framework/data/adonet/oracle-and-adonet

## 110. dba:q294234:a294245 — partially_supported_scoped
Tablespace birden fazla datafile içerebilir; dosyalar otomatik aynı verinin aynaları değildir. Sırf datafile eklemek bütün I/O sorunlarını çözmez.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/physical-storage-structures.html

## 111. dba:q217237:a217239 — partially_supported_scoped
RMAN root veya PDB bağlantısına göre PLUGGABLE DATABASE backup kapsamı değişir. Yetki/ARCHIVELOG/redo ve recovery gereği ayrıca gerekir; tek backup komutu bütün kurtarma planı değildir.
- https://docs.oracle.com/cd/F19136_01/multi/multitenant-administrators-guide.pdf

## 112. dba:q316432:a316437 — partially_supported_scoped
TRUNC sayının basamaklarını keser; negatif precision yüzlük sınır üretmede kullanılabilir. Boş/gap grupları ve sınır dahil oluşu veri modeline göre ayrıca kontrol edilir.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/TRUNC-number.html

## 113. dba:q283492:a283504 — partially_supported_scoped
Common user container-specific default tablespace/quota ayarları CONTAINER kapsamına bağlıdır. Root'taki quota PDB okuma yetkisi veya root dışı aynı tablespace varlığı sağlamaz.
- https://docs.oracle.com/database/121/SQLRF/statements_4003.htm

## 114. dba:q276580:a276701 — partially_supported_scoped
Data Guard ortamında RMAN backup/recovery stratejisi ayrıca tanımlanır; standby ile yedek saklama/PITR ihtiyacı aynı değildir. Logical ve physical standby backup uyumluluğu ayrılır.
- https://docs.oracle.com/en/database/oracle/oracle-database/21/sbydb/using-RMAN-in-oracle-data-guard-configurations.html

## 115. dba:q260375:a260378 — partially_supported_scoped
Online segment shrink ASSM ve ilgili nesne/row movement koşullarına bağlıdır. Segment boşluğu, high-water mark ve datafile resize farklı konulardır; delete otomatik dosya küçültmez.
- https://docs.oracle.com/database/121/ADMIN/E41484-15.pdf

## 116. dba:q320476:a320480 — partially_supported_scoped
RAC snapshot controlfile tüm gerekli instance'ların erişebildiği shared storage'da olmalıdır. ORA-00245 için bu konum kontrolü belgeli; her hata için tek neden olduğu iddia edilmez.
- https://docs.oracle.com/en/database/oracle/oracle-database/18/bradv/backing-up-database.html

## 117. dba:q325775:a325776 — partially_supported_scoped
Incremental backup block değişim bilgisi/BCT kullanabilir. Backup alınırken archive logdan fark bulma ile restore sonrası recovery redo ihtiyacı birbirinden ayrıdır.
- https://docs.oracle.com/en/database/oracle/oracle-database/18/bradv/backing-up-database.html

## 118. dba:q239646:a239647 — partially_supported_scoped
MOD bölüm kalanını, TRUNC kesmeyi sağlar; pozitif tamsayıyı ikiliye çevirme yaklaşımı anlaşılır. Negatif sayı/ölçek/taşma ve PRAGMA UDF desteği onaylanmadı.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/MOD.html

## 119. dba:q207346:a207352 — partially_supported_scoped
Permanent BIGFILE resize ve temporary tablespace shrink farklı işlemlerdir. Hedef boyut dosyadaki extents sınırına bağlıdır; örnekteki 80G güvenli hedef sayılmaz.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/ALTER-TABLESPACE.html

## 120. dba:q338375:a338379 — partially_supported_scoped
RMAN channel RATE backup I/O throttle seçeneğidir; sınır throughput ve bitiş süresini etkileyebilir. Bu her network bottleneck'ini gidermez; uygulama gecikmesi ölçülmelidir.
- https://docs.oracle.com/en/database/oracle/oracle-database/18/bradv/configuring-rman-client-advanced.html

## 121. dba:q208659:a208670 — partially_supported_scoped
Oracle NOT NULL constraint inline bildirilir; mevcut sütun ALTER TABLE MODIFY ile ele alınabilir. NULL veriler/yetki/kilit koşulları kontrol edilmeden DDL uygulanmamalı.
- https://docs.oracle.com/database/121/SQLRF/E41329-25.pdf

## 122. dba:q204762:a204764 — partially_supported_scoped
Default partition attributes ve mevcut segmentlerin taşınması ayrıdır. Interval subpartition için template de etkili olabilir; tablo tipine göre syntax değişir.
- https://docs.oracle.com/database/121/VLDBG/GUID-C003E6DB-3867-4407-86D2-A51F30AF07CC.htm

## 123. dba:q261168:a261199 — insufficient_support
_optimizer_filter_pushdown için müşteri tarafından değiştirilebilen/desteklenen bir ayar olduğunu gösteren erişilebilir resmî belge bulunamadı. Yalnız yazarın oturum ayarı sonrası bildirdiği tarihsel sonuç; genel komut değil.

## 124. dba:q279016:a279017 — partially_supported_scoped
RMAN duplication auxiliary instance'ı kapatıp yeniden açabilir; bağlantı/service/static registration önkoşulları önemlidir. Kaynaktaki belirli SID/Oracle Home ve UR=A ayarı genel reçete sayılmaz.
- https://docs.oracle.com/en/database/oracle/oracle-database/18/spmsu/starting-the-auxiliary-instance.html

## 125. dba:q224964:a224987 — partially_supported_scoped
CREATE TABLE varsayılan olarak heap-organized table oluşturur; IOT primary key index yapısında tutulur. Diğer DBMS'ler ve tüm clustered index ayrıntıları onay kapsamı dışında.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/tables-and-table-clusters.html

## 126. dba:q218653:a218654 — partially_supported_scoped
Backup piece ENCRYPTED alanı şifreleme durumunu raporlar. Tüm backup set/keystore kullanılabilirliğini veya restore başarısını tek satır göstermeye yetmez; metadata görünürlüğü kontrol edilir.
- https://docs.oracle.com/en/database/oracle/oracle-database/12.2/bradv/reporting-rman-operations.html

## 127. dba:q216818:a216832 — partially_supported_scoped
UNION/UNION ALL concurrent branch execution sürüm/OFE/plan ve PQ_CONCURRENT_UNION koşullarına bağlıdır. Oracle12c+ her UNION otomatik paraleldir iddiası yoktur.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/vldbg/types-parallelism.html

## 128. dba:q199118:a199125 — partially_supported_scoped
LAG/FIRST_VALUE partition/order temelli analitik yaklaşımı desteklenir. Aynı mbr sırası/tie, window ve NULL davranışı gerçek veriyle kontrol edilmeli; örnek SQL bütünü çalıştırılmadı.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Analytic-Functions.html

## 129. dba:q314858:a314861 — insufficient_support
SQLPlus SET LONG çıktı sınırları belgeli; LONG ile LONG RAW farklıdır. Kaynaktaki SQLPlus LONG RAW hiç gösteremez hükmünü bu erişilebilir belgede doğrulayamadım; kesin araç yetersizliği iddiası kaldırılmalı.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqpug/SET-system-variable-summary.html

## 130. dba:q253377:a253379 — partially_supported_scoped
GNU date +format biçimli tarih üretir; Bash substitution ile RMAN log adına eklemek shell işlemidir. Unique saniye damgası eşzamanlı tüm süreçler için benzersizlik garantisi değildir.
- https://www.gnu.org/software/coreutils/manual/coreutils.pdf

## 131. dba:q306941:a306942 — partially_supported_scoped
GROUP BY/HAVING ile filtrelenmiş distinct tür sayısını aranan tür sayısıyla karşılaştırma mümkündür. Duplicate/NULL ve dinamik seçim sayısı kontrol edilmeli; OR ile AND anlamı ayrılmalıdır.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/SELECT.html

## 132. dba:q232920:a232922 — partially_supported_scoped
CONFIGURE ilgili seçeneği CLEAR ile varsayılana döndürebilir. Tek global clear-all prosedürü verilmez; retention gibi varsayılanlara dönüşün operasyonel etkisi vardır.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/rcmrf/CONFIGURE.html

## 133. dba:q230549:a230550 — partially_supported_scoped
CONFIGURE kalıcı; RUN içi ALLOCATE CHANNEL job kapsamlı ayardır. MAXPIECESIZE backup piece boyutunu etkiler ve channel adı/device type koşulları gerekir.
- https://docs.oracle.com/en/database/oracle/oracle-database/18/bradv/configuring-rman-client-advanced.html

## 134. dba:q297829:a297899 — insufficient_support
PGA hedefleri bellek yönetimini etkiler; kaynakta 10G→5G değişikliğinin AIX ORA-04030'u neden çözdüğü veya OS 10G ayıramadığı doğrulanmadı. Yalnız vaka bildirimi korunur, değer önerisi yapılmaz.
- https://docs.oracle.com/en/database/oracle/oracle-database/26/admin/managing-memory.html

## 135. dba:q217878:a217941 — partially_supported_scoped
DBCA seed template datafile backups içerir, nonseed template içermez. Kaynakta verilen 5dk/60dk süreleri donanıma/opsiyonlara bağlıdır; garanti değildir.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/admqs/installing-oracle-database-creating-database.html

## 136. dba:q291616:a291622 — partially_supported_scoped
Dynamic SQL placeholder/USING eşleşmesi gereklidir; SQL statement ile PL/SQL block tekrar eden ad semantiği farklı olabilir. Sabit SQL null filtre alternatifi yalnız anlam/plan değerlendirmesiyle kullanılmalı.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/lnpls/native-dynamic-sql.html

## 137. dba:q287169:a287184 — partially_supported_scoped
ORA-39014 worker erken çıkışını bildirir; gerçek worker/alert/trace hataları birlikte değerlendirilmelidir. PARALLEL tek kanıtlanmış root cause değildir.
- https://docs.oracle.com/en/error-help/db/ora-39014/

## 138. dba:q274063:a274067 — partially_supported_scoped
Table alias sorgu içi addır; schema qualification nesnenin sahibini belirler. A1 ayrı tablo/şema veya performans garantisi değildir.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/SELECT.html

## 139. dba:q249079:a249147 — partially_supported_scoped
TNS_ADMIN Oracle Net config dosyalarının konumunu belirleyebilir. Instant Client için tam server ORACLE_HOME kurulumu zorunlu sonuç değildir; mimari/ODBC/TNS alias ayrıca kontrol edilir.
- https://docs.oracle.com/en/database/oracle/oracle-database/21/ntcli/environment-variables-oracle-instant-client.html

## 140. dba:q244316:a244319 — partially_supported_scoped
LISTAGG'den önce duplicate değerleri ayırma ile yeni sürümlerde LISTAGG DISTINCT farklı yollardır. 19c syntax'ı 11.2'ye doğrudan taşınmamalı; kaynak distinct alt sorgusu eski sürüm için açıklanır.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/tutorial-avoid-errors-listagg-function/

## 141. dba:q244148:a244300 — partially_supported_scoped
NOT IN alt sorgusu hiç satır döndürmezse tüm satırlar dönebilir; boş küme ile içinde NULL olan küme farklıdır. Bu ayrım kaynak sorununun dar kapsamını destekler.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/IN-Condition.html

## 142. dba:q241288:a241290 — insufficient_support
Data Pump VERSION/uyumluluk kısıtları belgeli; dump header 4.1/5.1 ile 12.1/12.2 birebir eşleştirmesi erişilemeyen MOS notuna dayanıyor. Bu kesin sürüm teşhisi doğrulanmış sayılmadı.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sutil/oracle-data-pump-overview.html

## 143. dba:q234758:a234763 — partially_supported_scoped
atomic_refresh=true resmî belgede tek transaction ve tek point-in-time olarak açıklanır. Bu belirli 10:00 AM hedef SCN'yi kullanıcı seçmiş gibi garanti etmez; Maybe flashback bitmiş çözüm değildir.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_MVIEW.html

## 144. dba:q229925:a229930 — partially_supported_scoped
START WITH kök seçimini, CONNECT BY hiyerarşi ilişkisini belirler; kök/çocuk filtreleri ayrıdır. Source cümlesindeki siblings ifadesi bütün semantics yerine geçmez.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Hierarchical-Queries.html

## 145. dba:q227632:a227723 — partially_supported_scoped
Local OS authentication SYSDBA için OSDBA grubu yetkileri önemlidir; her root/oracle kullanıcı adı evrensel ölçüt değildir. Container image, OS group ve ortam ayrıca kontrol edilir.
- https://docs.oracle.com/cd/E18283_01/server.112/e17120/dba006.htm

## 146. dba:q213548:a215379 — partially_supported_scoped
ORA-00443 background process başlamadığını bildirir; dosya korumaları/konum/bellek kontrolü önerilir. Kaynaktaki diagnostic_dest parent g+w nedeni tek vaka olarak kalır, her 443 için çözüm değildir.
- https://docs.oracle.com/en/error-help/db/ora-00443/

## 147. dba:q213363:a213427 — partially_supported_scoped
V$SESSION PROGRAM istemci program bilgisidir; farklı istemci/session bağlamını kıyaslama desteklenir. Listener log bütün session ayarlarını içermez; login trigger bu vakada kanıtlanmamış.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/V-SESSION.html

## 148. dba:q211434:a211443 — partially_supported_scoped
Orphan backup incarnation'ın mevcut restore yolunun doğrudan atası olmamasıyla ilişkilidir. Her RESETLOGS eski bütün backup'ları otomatik siler iddiası veya DELETE OBSOLETE reçetesi çıkarılmaz.
- https://docs.oracle.com/cd/A91202_01/901_doc/server.901/a90135/rmanconb.htm

## 149. dba:q205004:a205007 — insufficient_support
Data Modeler design .dmd ve alt klasör yapısını kullanır; yalnız logical klasörünü başka model içine kopyalamanın desteklenen kurtarma prosedürü olduğu doğrulanmadı. Dosya yedeği olmadan uygulanabilir talimat sayılmaz.
- https://docs.oracle.com/en/database/oracle/sql-developer-data-modeler/21.2/dmdug/data-modeler-concepts-usage.html

## 150. dba:q196352:a196398 — partially_supported_scoped
Write-ahead protocol: DBW dirty buffer yazmadan ilgili redo diske yazılır. Uncommitted bloklar asla diske yazılmaz cümlesi onaylanmadı; crash recovery undo/redo ile tutarlılığı ele alır, her corruption türünü dışlamaz.
- https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/process-architecture.html

## Uygulama güncellemesi

150 kayıt ve embedding güncellendi. Diğer 296 kayıt/chunk aynı kaldı; özgün soru-cevap ve lisanslar korundu. Toplam 446 kayıt. Her güncellenen kayıt için içerik hash, durum, metadata ve 1024 boyutlu embedding ile kendi vektöründe ilk üç hazırlık kontrolü geçti. Bu kontrol doğal dil yanıt kalitesi testi değildir.
